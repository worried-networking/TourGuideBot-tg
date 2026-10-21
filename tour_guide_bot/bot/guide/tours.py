import html
from asyncio import Task, sleep
from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAudio,
    InputMediaPhoto,
    InputFile,
    InputMediaVideo,
    Update,
)
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tour_guide_bot import t
from tour_guide_bot.bot.guide import log
from tour_guide_bot.helpers.telegram import get_tour_title
from tour_guide_bot.helpers.tours_selector import SelectTourHandler
from tour_guide_bot.models.guide import (
    MessageType,
    Subscription,
    Tour,
    TourSection,
    TourTranslation,
)
from tour_guide_bot.models.settings import Settings, SettingsKey


class ToursCommandHandler(SelectTourHandler):
    SKIP_TOUR_SELECTION_IF_SINGLE = True

    STATE_TOUR_IN_PROGRESS = 1

    # Running section sends by user id; deliberately not in the (pickled) context.
    _running_sends: dict[int, Task] = {}

    @classmethod
    def get_handlers(cls):
        return [
            ConversationHandler(
                entry_points=[CommandHandler("tours", cls.partial(cls.start))],
                states={
                    cls.STATE_SELECT_TOUR: cls.get_select_tour_handlers(),
                    cls.STATE_TOUR_IN_PROGRESS: [
                        CallbackQueryHandler(
                            cls.partial(cls.tour_change_section),
                            r"^tour_change_section:(\d+):(\d+)$",
                        ),
                    ],
                },
                fallbacks=[
                    CommandHandler("cancel", cls.partial(cls.cancel)),
                    CallbackQueryHandler(cls.partial(cls.cancel), "cancel"),
                    MessageHandler(filters.ALL, cls.partial(cls.nop_handler)),
                ],
                name="guest-tour",
                persistent=True,
                # A section whose send failed or was interrupted leaves no buttons
                allow_reentry=True,
            )
        ]

    async def get_tour(self, guest_id: int, tour_id: int) -> Subscription | None:
        bought_tour: Subscription | None = await self.db_session.scalar(
            select(Subscription)
            .options(
                selectinload(Subscription.tour)
                .selectinload(Tour.translations)
                .selectinload(TourTranslation.sections)
                .selectinload(TourSection.content)
            )
            .where(
                (Subscription.guest_id == guest_id)
                & (Subscription.tour_id == tour_id)
                & (Subscription.expire_ts >= datetime.now())
            )
        )

        return bought_tour

    async def display_section(
        self,
        translation: TourTranslation,
        position: int,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.delete_message()

        user = await self.get_user(update, context)

        if position < 0 or len(translation.sections) <= position:
            await self.edit_or_reply_text(
                update,
                context,
                t(user.language).pgettext(
                    "bot-generic", "Something went wrong; please try again."
                ),
            )
            return

        section = translation.sections[position]

        is_last_section = position == len(translation.sections) - 1

        delay_between_messages_state = await Settings.load(
            self.db_session, SettingsKey.delay_between_messages, create=True
        )
        protect_content = (
            await Settings.load(
                self.db_session, SettingsKey.protect_content, create=True
            )
        ).is_enabled

        delay = delay_between_messages_state.value

        # The send runs in a background task after the handler (and its db
        # session) is gone, so only plain data is passed to it.
        contents = [(c.message_type, c.content) for c in section.content]

        user_id = update.effective_user.id
        self.cancel_running_send(user_id)

        task = context.application.create_task(
            self.send_section(
                update,
                context,
                update.effective_chat.id,
                contents,
                delay,
                protect_content,
                user.language,
                translation.id,
                position,
                is_last_section,
            ),
            update=update,
        )
        self._running_sends[user_id] = task
        task.add_done_callback(
            lambda t_, user_id=user_id: self._forget_send(user_id, t_)
        )

        if not is_last_section:
            return self.STATE_TOUR_IN_PROGRESS

        return ConversationHandler.END

    @classmethod
    def cancel_running_send(cls, user_id: int):
        task = cls._running_sends.pop(user_id, None)
        if task and not task.done():
            task.cancel()

    @classmethod
    def cancel_all_running_sends(cls):
        for user_id in list(cls._running_sends):
            cls.cancel_running_send(user_id)

    @classmethod
    def _forget_send(cls, user_id: int, task: Task):
        if cls._running_sends.get(user_id) is task:
            del cls._running_sends[user_id]

    async def cancel_without_conversation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        if update.effective_user:
            self.cancel_running_send(update.effective_user.id)

        await super().cancel_without_conversation(update, context)

    @staticmethod
    async def reupload(bot, file_id: str, filename: str) -> InputFile:
        """Fetch a file for sending again as a different type: file_ids are typed."""
        file = await bot.get_file(file_id)
        return InputFile(bytes(await file.download_as_bytearray()), filename=filename)

    @classmethod
    async def send_blocked_file(
        cls,
        bot,
        chat_id: int,
        file_id: str,
        filename: str,
        caption: str | None,
        protect_content: bool,
        language: str,
        explain: bool,
    ) -> bool:
        # Telegram turns Opus audio back into a voice message (and an mp4 back
        # into a video note), so send the bare file without the content type
        # detection, and explain why it isn't played.
        await bot.send_document(
            chat_id,
            await cls.reupload(bot, file_id, filename),
            caption=caption,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_content_type_detection=True,
            disable_notification=True,
            protect_content=protect_content,
        )
        if explain:
            # Italic, to set the bot's own note apart from the tour content
            explanation = t(language).pgettext(
                "guide-tour",
                "Your privacy settings block voice messages, so some parts of "
                "the tour can't be shown properly. To fix this, allow voice "
                "messages for this bot in Settings → Privacy and Security → "
                "Voice Messages.",
            )
            await bot.send_message(
                chat_id,
                "<i>%s</i>" % html.escape(explanation),
                parse_mode=ParseMode.HTML,
                disable_notification=True,
            )

        return True

    async def send_section(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        contents: Sequence[tuple[MessageType, dict]],
        delay: str,
        protect_content: bool,
        language: str,
        translation_id: int,
        position: int,
        is_last_section: bool,
    ):
        # Runs as a background task: must not touch self.db_session.
        bot = context.bot
        # Explain the blocked voice messages only once per section
        voice_messages_blocked = False

        for message_type, content_data in contents:
            chat_action = ChatAction.TYPING
            match message_type:
                case MessageType.location:
                    chat_action = (
                        ChatAction.TYPING
                    )  # todo change to ChatAction.FIND_LOCATION
                case MessageType.voice | MessageType.audio:
                    chat_action = ChatAction.UPLOAD_VOICE
                case MessageType.video_note:
                    chat_action = ChatAction.UPLOAD_VIDEO_NOTE
                case MessageType.video:
                    chat_action = ChatAction.UPLOAD_VIDEO
                case MessageType.photo:
                    chat_action = ChatAction.UPLOAD_PHOTO
                case MessageType.media_group:
                    match content_data["files"]:
                        case MessageType.audio:
                            chat_action = ChatAction.UPLOAD_VOICE
                        case MessageType.video:
                            chat_action = ChatAction.UPLOAD_VIDEO
                        case MessageType.photo:
                            chat_action = ChatAction.UPLOAD_PHOTO

            if chat_action and int(delay) > 0:
                await bot.send_chat_action(chat_id=chat_id, action=chat_action)
                await sleep(float(delay))

            match message_type:
                case MessageType.text:
                    await bot.send_message(
                        chat_id,
                        content_data["text"],
                        ParseMode.MARKDOWN_V2,
                        disable_web_page_preview=True,
                        disable_notification=True,
                        protect_content=protect_content,
                    )

                case MessageType.location:
                    await bot.send_location(
                        chat_id,
                        content_data["latitude"],
                        content_data["longitude"],
                        disable_notification=True,
                        protect_content=protect_content,
                    )

                case MessageType.voice:
                    try:
                        await bot.send_voice(
                            chat_id,
                            content_data["files"][0]["file_id"],
                            caption=content_data["files"][0].get("caption"),
                            parse_mode=ParseMode.MARKDOWN_V2,
                            disable_notification=True,
                            protect_content=protect_content,
                        )
                    except BadRequest as e:
                        if e.message != "Voice_messages_forbidden":
                            raise

                        # The user's privacy settings block voice messages
                        voice_messages_blocked = await self.send_blocked_file(
                            bot,
                            chat_id,
                            content_data["files"][0]["file_id"],
                            "voice.ogg",
                            content_data["files"][0].get("caption"),
                            protect_content,
                            language,
                            explain=not voice_messages_blocked,
                        )

                case MessageType.video_note:
                    try:
                        await bot.send_video_note(
                            chat_id,
                            content_data["files"][0]["file_id"],
                            disable_notification=True,
                            protect_content=protect_content,
                        )
                    except BadRequest as e:
                        if e.message != "Voice_messages_forbidden":
                            raise

                        # The same privacy setting blocks video notes
                        voice_messages_blocked = await self.send_blocked_file(
                            bot,
                            chat_id,
                            content_data["files"][0]["file_id"],
                            "video.mp4",
                            None,
                            protect_content,
                            language,
                            explain=not voice_messages_blocked,
                        )

                case MessageType.audio:
                    await bot.send_audio(
                        chat_id,
                        content_data["files"][0]["file_id"],
                        caption=content_data["files"][0].get("caption"),
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_notification=True,
                        protect_content=protect_content,
                    )

                case MessageType.video:
                    await bot.send_video(
                        chat_id,
                        content_data["files"][0]["file_id"],
                        caption=content_data["files"][0].get("caption"),
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_notification=True,
                        protect_content=protect_content,
                    )

                case MessageType.photo:
                    await bot.send_photo(
                        chat_id,
                        content_data["files"][0]["file_id"],
                        caption=content_data["files"][0].get("caption"),
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_notification=True,
                        protect_content=protect_content,
                    )

                case MessageType.animation:
                    await bot.send_animation(
                        chat_id,
                        content_data["files"][0]["file_id"],
                        caption=content_data["files"][0].get("caption"),
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_notification=True,
                        protect_content=protect_content,
                    )

                case MessageType.media_group:
                    media_group = []

                    for f in content_data["files"]:
                        match MessageType[f["type"]]:
                            case MessageType.audio:
                                media_group.append(
                                    InputMediaAudio(
                                        f["file_id"],
                                        caption=f.get("caption"),
                                        parse_mode=ParseMode.MARKDOWN_V2,
                                    )
                                )
                            case MessageType.video:
                                media_group.append(
                                    InputMediaVideo(
                                        f["file_id"],
                                        caption=f.get("caption"),
                                        parse_mode=ParseMode.MARKDOWN_V2,
                                    )
                                )
                            case MessageType.photo:
                                media_group.append(
                                    InputMediaPhoto(
                                        f["file_id"],
                                        caption=f.get("caption"),
                                        parse_mode=ParseMode.MARKDOWN_V2,
                                    )
                                )

                    await bot.send_media_group(
                        chat_id,
                        media_group,
                        disable_notification=True,
                        protect_content=protect_content,
                    )

        if not is_last_section:
            if int(delay) > 0:
                await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                await sleep(float(delay))

            await self.reply_text(
                update,
                context,
                t(language).pgettext("guide-tour", "Are you ready to continue?"),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                t(language).pgettext("guide-tour", "Next section"),
                                callback_data="tour_change_section:%d:%d"
                                % (translation_id, position + 1),
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                t(language).pgettext("bot-generic", "Abort"),
                                callback_data="cancel",
                            )
                        ],
                    ]
                ),
            )
            return self.STATE_TOUR_IN_PROGRESS

        return ConversationHandler.END

    async def display_first_section(
        self, tour: Tour, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        tour: Tour = await self.db_session.scalar(
            select(Tour)
            .options(
                selectinload(Tour.translations)
                .selectinload(TourTranslation.sections)
                .selectinload(TourSection.content)
            )
            .where(Tour.id == tour.id)
        )

        translations = {
            translation.language: translation for translation in tour.translations
        }

        user = await self.get_user(update, context)

        if user.language not in translations:
            log.warning(
                t()
                .pgettext(
                    "cli",
                    "Tour #{0} doesn't have a language {1} preferred by the user {2}.",
                )
                .format(tour.id, user.language, user.id)
            )
            if context.application.default_language not in translations:
                log.error(
                    t()
                    .pgettext(
                        "cli", "Tour #{0} doesn't have a default app language {1}."
                    )
                    .format(tour.id, context.application.default_language)
                )
                await self.edit_or_reply_text(
                    update,
                    context,
                    t(user.language).pgettext(
                        "bot-generic", "Something went wrong; please try again."
                    ),
                )
                return ConversationHandler.END
            else:
                translation = translations[context.application.default_language]
        else:
            translation = translations[user.language]

        return await self.display_section(translation, 0, update, context)

    async def tour_change_section(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        user = await self.get_user(update, context)

        translation: TourTranslation | None = await self.db_session.scalar(
            select(TourTranslation)
            .options(
                selectinload(TourTranslation.sections).selectinload(TourSection.content)
            )
            .where(TourTranslation.id == int(context.matches[0].group(1)))
        )
        if not translation:
            await update.callback_query.answer()
            await self.edit_or_reply_text(
                update,
                context,
                t(user.language).pgettext(
                    "bot-generic", "Something went wrong; please try again."
                ),
            )
            return

        bought_tour = await self.get_tour(user.guest_id, translation.tour_id)
        if not bought_tour:
            await update.callback_query.answer()
            await self.edit_or_reply_text(
                update,
                context,
                t(user.language).pgettext(
                    "guide-tour",
                    "Unfortunately, you don't have access to the requested tour.",
                ),
            )

            return ConversationHandler.END

        return await self.display_section(
            translation, int(context.matches[0].group(2)), update, context
        )

    async def after_tour_selected(
        self,
        tour: Tour,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        is_single_tour: bool,
    ):
        language = await self.get_language(update, context)
        msg = ""
        if is_single_tour:
            msg = (
                t(language)
                .pgettext(
                    "guest-tour",
                    "Only one tour is available for you: {}.",
                )
                .format(get_tour_title(tour, language, context))
                + "\n"
            )
        else:
            msg = (
                t(language)
                .pgettext(
                    "guest-tour",
                    "You have selected the tour {}.",
                )
                .format(get_tour_title(tour, language, context))
                + "\n"
            )

        msg += t(language).pgettext(
            "guest-tour",
            "Now the bot will send you several messages, please start the"
            " tour with the following one 👇",
        )

        # The original message from the callback will be deleted later, down the trace.
        await self.reply_text(update, context, msg)
        return await self.display_first_section(tour, update, context)

    def get_tour_selection_message(self, language: str) -> str:
        return t(language).pgettext(
            "guide-tour", "Please select a tour you want to start."
        )

    async def handle_no_tours_found(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        language = await self.get_language(update, context)
        await update.message.reply_text(
            t(language).pgettext(
                "guest-tour",
                "Unfortunately, no tours are available for"
                " you at the moment. Approving somebody for a tour takes"
                " a while, but if you feel like a mistake was made, don't"
                " hesitate to contact me! The bot's profile should provide"
                " all the required info.",
            )
        )
        return ConversationHandler.END

    async def get_acceptable_tours(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> Sequence[Tour]:
        user = await self.get_user(update, context)
        subscriptions = await self.db_session.scalars(
            select(Subscription)
            .options(
                selectinload(Subscription.tour).selectinload(Tour.translations),
            )
            .where(
                (Subscription.guest == user.guest)
                & (Subscription.expire_ts >= datetime.now())
            )
        )

        return [subscription.tour for subscription in subscriptions]

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_user(update, context)

        bought_tours_without_notifications: Sequence[Subscription] = (
            await self.db_session.scalars(
                select(Subscription).where(
                    (Subscription.guest == user.guest)
                    & (Subscription.is_user_notified == False)
                )
            )
        ).all()

        for bought_tour in bought_tours_without_notifications:
            bought_tour.is_user_notified = True
            self.db_session.add(bought_tour)

        if len(bought_tours_without_notifications):
            await self.db_session.commit()

        return await self.send_tour_selector(update, context)
