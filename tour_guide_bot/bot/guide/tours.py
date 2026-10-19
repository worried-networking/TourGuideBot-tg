from asyncio import sleep
from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAudio,
    InputMediaPhoto,
    InputMediaVideo,
    Update,
)
from telegram.constants import ChatAction, ParseMode
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

        bot = context.bot
        chat_id = update.effective_chat.id

        is_last_section = position == len(translation.sections) - 1

        delay_between_messages_state = await Settings.load(
            self.db_session, SettingsKey.delay_between_messages, create=True
        )
        protect_content = (
            await Settings.load(
                self.db_session, SettingsKey.protect_content, create=True
            )
        ).is_enabled

        for content in section.content:
            chat_action = ChatAction.TYPING
            match content.message_type:
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
                    match content.content["files"]:
                        case MessageType.audio:
                            chat_action = ChatAction.UPLOAD_VOICE
                        case MessageType.video:
                            chat_action = ChatAction.UPLOAD_VIDEO
                        case MessageType.photo:
                            chat_action = ChatAction.UPLOAD_PHOTO

            if chat_action and int(delay_between_messages_state.value) > 0:
                await bot.send_chat_action(chat_id=chat_id, action=chat_action)
                await sleep(float(delay_between_messages_state.value))

            match content.message_type:
                case MessageType.text:
                    await bot.send_message(
                        chat_id,
                        content.content["text"],
                        ParseMode.MARKDOWN_V2,
                        disable_web_page_preview=True,
                        disable_notification=True,
                        protect_content=protect_content,
                    )

                case MessageType.location:
                    await bot.send_location(
                        chat_id,
                        content.content["latitude"],
                        content.content["longitude"],
                        disable_notification=True,
                        protect_content=protect_content,
                    )

                case MessageType.voice:
                    await bot.send_voice(
                        chat_id,
                        content.content["files"][0]["file_id"],
                        caption=content.content["files"][0].get("caption"),
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_notification=True,
                        protect_content=protect_content,
                    )

                case MessageType.video_note:
                    await bot.send_video_note(
                        chat_id,
                        content.content["files"][0]["file_id"],
                        caption=content.content["files"][0].get("caption"),
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_notification=True,
                        protect_content=protect_content,
                    )

                case MessageType.audio:
                    await bot.send_audio(
                        chat_id,
                        content.content["files"][0]["file_id"],
                        caption=content.content["files"][0].get("caption"),
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_notification=True,
                        protect_content=protect_content,
                    )

                case MessageType.video:
                    await bot.send_video(
                        chat_id,
                        content.content["files"][0]["file_id"],
                        caption=content.content["files"][0].get("caption"),
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_notification=True,
                        protect_content=protect_content,
                    )

                case MessageType.photo:
                    await bot.send_photo(
                        chat_id,
                        content.content["files"][0]["file_id"],
                        caption=content.content["files"][0].get("caption"),
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_notification=True,
                        protect_content=protect_content,
                    )

                case MessageType.animation:
                    await bot.send_animation(
                        chat_id,
                        content.content["files"][0]["file_id"],
                        caption=content.content["files"][0].get("caption"),
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_notification=True,
                        protect_content=protect_content,
                    )

                case MessageType.media_group:
                    media_group = []

                    for f in content.content["files"]:
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
            if int(delay_between_messages_state.value) > 0:
                await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                await sleep(float(delay_between_messages_state.value))

            await self.reply_text(
                update,
                context,
                t(user.language).pgettext("guide-tour", "Are you ready to continue?"),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                t(user.language).pgettext("guide-tour", "Next section"),
                                callback_data="tour_change_section:%d:%d"
                                % (translation.id, position + 1),
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                t(user.language).pgettext("bot-generic", "Abort"),
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
