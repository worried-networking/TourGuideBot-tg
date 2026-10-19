import os
from abc import ABC
from typing import ClassVar

import ffmpeg
from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tour_guide_bot import t
from tour_guide_bot.bot.admin import log
from tour_guide_bot.helpers.telegram import AdminProtectedBaseHandlerCallback
from tour_guide_bot.models.guide import MessageType, TourSectionContent
from tour_guide_bot.models.settings import Settings, SettingsKey


class AddContentCommandHandler(AdminProtectedBaseHandlerCallback, ABC):
    STATE_TOUR_AUDIO_CONVERT_CONFIRMATION: ClassVar[int] = -30
    STATE_TOUR_AUDIO_CONVERT_VOICE_CHECK: ClassVar[int] = -31

    @classmethod
    def get_add_content_handlers(cls):
        return [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & ~filters.UpdateType.EDITED,
                cls.partial(cls.translation_section_content_add_text),
            ),
            MessageHandler(
                filters.LOCATION & ~filters.UpdateType.EDITED,
                cls.partial(cls.translation_section_content_add_location),
            ),
            MessageHandler(
                filters.ANIMATION & ~filters.UpdateType.EDITED,
                cls.partial(cls.translation_section_content_add_animation),
            ),
            ConversationHandler(
                entry_points=[
                    MessageHandler(
                        filters.AUDIO & ~filters.UpdateType.EDITED,
                        cls.partial(cls.translation_section_content_add_audio),
                    )
                ],
                states={
                    cls.STATE_TOUR_AUDIO_CONVERT_CONFIRMATION: [
                        CallbackQueryHandler(
                            cls.partial(
                                cls.translation_section_content_add_audio_convert
                            ),
                            "convert_audio",
                        ),
                        CallbackQueryHandler(
                            cls.partial(
                                cls.translation_section_content_add_store_audio
                            ),
                            "store_audio_as_is",
                        ),
                        CallbackQueryHandler(
                            cls.partial(
                                cls.translation_section_content_add_mute_and_store_audio
                            ),
                            "disable_conversion_and_store_audio_as_is",
                        ),
                    ],
                    cls.STATE_TOUR_AUDIO_CONVERT_VOICE_CHECK: [
                        CallbackQueryHandler(
                            cls.partial(
                                cls.translation_section_content_add_audio_convert
                            ),
                            "convert_audio",
                        ),
                        CallbackQueryHandler(
                            cls.partial(
                                cls.translation_section_content_add_store_audio
                            ),
                            "store_audio_as_is",
                        ),
                        CallbackQueryHandler(
                            cls.partial(
                                cls.translation_section_content_add_store_voice
                            ),
                            "store_voice",
                        ),
                    ],
                },
                fallbacks=[
                    CallbackQueryHandler(
                        cls.partial(cls.cancel_audio_conversion), "cancel"
                    ),
                    CommandHandler("cancel", cls.partial(cls.cancel_audio_conversion)),
                    MessageHandler(filters.COMMAND, cls.partial(cls.unknown_command)),
                    MessageHandler(filters.ALL, cls.partial(cls.unexpected_message)),
                ],
                name="admin-tour-audio-convert",
                persistent=True,
            ),
            MessageHandler(
                filters.VOICE & ~filters.UpdateType.EDITED,
                cls.partial(cls.translation_section_content_add_voice),
            ),
            MessageHandler(
                filters.VIDEO & ~filters.UpdateType.EDITED,
                cls.partial(cls.translation_section_content_add_video),
            ),
            MessageHandler(
                filters.VIDEO_NOTE & ~filters.UpdateType.EDITED,
                cls.partial(cls.translation_section_content_add_video_note),
            ),
            MessageHandler(
                filters.PHOTO & ~filters.UpdateType.EDITED,
                cls.partial(cls.translation_section_content_add_photo),
            ),
            MessageHandler(
                filters.ALL & ~filters.COMMAND & ~filters.UpdateType.EDITED,
                cls.partial(cls.translation_unknown_content),
            ),
        ]

    async def after_content_added(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        pass

    async def cancel_audio_conversion(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        user = await self.get_user(update, context)
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.delete_message()

        await self.reply_text(
            update, context, t(user.language).pgettext("bot-generic", "Cancelled.")
        )
        return ConversationHandler.END

    async def translation_section_content_add(
        self,
        message_id: int,
        context: ContextTypes.DEFAULT_TYPE,
        message_type: MessageType,
        text: str | None = None,
        media_group_id: str | None = None,
        file_id: str | None = None,
        file_caption=None,
        location=None,
    ):
        is_first = True
        async with context.application.content_add_lock:
            if media_group_id:
                content: TourSectionContent | None = await self.db_session.scalar(
                    select(TourSectionContent).where(
                        (
                            TourSectionContent.tour_section_id
                            == context.user_data["tour_section_id"]
                        )
                        & (TourSectionContent.media_group_id == media_group_id)
                    )
                )

                if content:
                    is_first = False

                    file = {
                        "file_id": file_id,
                        "message_id": message_id,
                        "type": message_type.name,
                    }

                    if file_caption:
                        file["caption"] = file_caption

                    files = content.content.pop("files")
                    files.append(file)

                    content.content["files"] = list(
                        sorted(files, key=lambda file: file["message_id"])
                    )

                    self.db_session.add(content)

            if is_first:
                is_first = True
                content = TourSectionContent()
                content.tour_section_id = context.user_data["tour_section_id"]
                if media_group_id:
                    content.media_group_id = media_group_id
                    content.message_type = MessageType.media_group
                else:
                    content.message_type = message_type

                content.position = context.user_data.get(
                    "tour_section_content_position", 0
                )

                if file_id:
                    file = {
                        "file_id": file_id,
                        "message_id": message_id,
                        "type": message_type.name,
                    }

                    if file_caption:
                        file["caption"] = file_caption

                    content.content = {"files": [file]}
                elif text:
                    content.content = {"text": text}
                elif location:
                    content.content = location

                self.db_session.add(content)

                context.user_data["tour_section_content_position"] = (
                    context.user_data.get("tour_section_content_position", 0) + 1
                )

        await self.db_session.commit()

        return is_first

    async def translation_section_content_add_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        await self.translation_section_content_add(
            update.message.message_id,
            context,
            MessageType.text,
            text=update.message.text_markdown_v2_urled,
        )
        language = await self.get_language(update, context)
        message = t(language).pgettext(
            "admin-tours", "The text was added to the section!"
        )
        message += " "
        message += t(language).pgettext(
            "admin-tours",
            "Add more data or send /done if you're finished with the section.",
        )
        await update.message.reply_text(message)

    async def translation_section_content_add_animation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        await self.translation_section_content_add(
            update.message.message_id,
            context,
            MessageType.animation,
            file_id=update.message.animation.file_id,
            file_caption=update.message.caption_markdown_v2_urled,
        )
        language = await self.get_language(update, context)
        message = t(language).pgettext(
            "admin-tours", "The animation was added to the section!"
        )
        message += " "
        message += t(language).pgettext(
            "admin-tours",
            "Add more data or send /done if you're finished with the section.",
        )
        await update.message.reply_text(message)

    async def translation_section_content_add_location(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        await self.translation_section_content_add(
            update.message.message_id,
            context,
            MessageType.location,
            location={
                "latitude": update.message.location.latitude,
                "longitude": update.message.location.longitude,
            },
        )
        language = await self.get_language(update, context)
        message = t(language).pgettext(
            "admin-tours", "The location was added to the section!"
        )
        message += " "
        message += t(language).pgettext(
            "admin-tours",
            "Add more data or send /done if you're finished with the section.",
        )
        await update.message.reply_text(message)

    async def translation_section_content_add_voice(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        await self.translation_section_content_add(
            update.message.message_id,
            context,
            MessageType.voice,
            file_id=update.message.voice.file_id,
            file_caption=update.message.caption_markdown_v2_urled,
        )

        await self._report_voice_saved(update, context)

    async def _report_voice_saved(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        language = await self.get_language(update, context)
        message = t(language).pgettext(
            "admin-tours", "The voice was added to the section!"
        )
        message += " "
        message += t(language).pgettext(
            "admin-tours",
            "Add more data or send /done if you're finished with the section.",
        )
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.delete_message()

        await self.reply_text(update, context, message)

    async def translation_section_content_add_video_note(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        await self.translation_section_content_add(
            update.message.message_id,
            context,
            MessageType.video_note,
            file_id=update.message.video_note.file_id,
            file_caption=update.message.caption_markdown_v2_urled,
        )

        language = await self.get_language(update, context)
        message = t(language).pgettext(
            "admin-tours", "The video note was added to the section!"
        )
        message += " "
        message += t(language).pgettext(
            "admin-tours",
            "Add more data or send /done if you're finished with the section.",
        )
        await update.message.reply_text(message)

    async def convert_audio(self, context: CallbackContext):
        bot = context.bot
        language = context.job.data["language"]

        try:
            file = await bot.get_file(context.user_data["audio_file_id"])
            original_audio_path = await file.download_to_drive()
        except Exception:
            log.exception(
                "Failed to download file %s", context.user_data["audio_file_id"]
            )
            await bot.edit_message_text(
                t(language).pgettext(
                    "admin-tours",
                    "Something went wrong when I tried to download your audio (see the details in the logs)."
                    " What should I do now?",
                ),
                chat_id=context.job.data["chat_id"],
                message_id=context.job.data["message_id"],
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                t(language).pgettext("bot-generic", "Try again"),
                                callback_data="convert_audio",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                t(language).pgettext(
                                    "admin-tours", "Store the original audio"
                                ),
                                callback_data="store_audio_as_is",
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
            return

        await bot.edit_message_text(
            t(language).pgettext("admin-tours", "File downloaded, converting..."),
            chat_id=context.job.data["chat_id"],
            message_id=context.job.data["message_id"],
        )

        destination_path = "%s.%s" % (original_audio_path, "ogg")
        try:
            process = (
                ffmpeg.input(original_audio_path)
                .output(destination_path, acodec="libopus", **{"b:a": "192000"})
                .run_async()
            )
            # TODO: the process is blocked here
            process.wait()
        except Exception:
            if os.path.isfile(destination_path):
                os.unlink(destination_path)

            log.exception(
                "Failed to convert file %s", context.user_data["audio_file_id"]
            )
            await bot.edit_message_text(
                t(language).pgettext(
                    "admin-tours",
                    "Something went wrong when I tried to convert the file."
                    " What should I do now?",
                ),
                chat_id=context.job.data["chat_id"],
                message_id=context.job.data["message_id"],
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                t(language).pgettext("bot-generic", "Try again"),
                                callback_data="convert_audio",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                t(language).pgettext(
                                    "admin-tours", "Store the original audio"
                                ),
                                callback_data="store_audio_as_is",
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
            return
        finally:
            os.unlink(original_audio_path)

        await bot.edit_message_text(
            t(language).pgettext("admin-tours", "File converted, uploading..."),
            chat_id=context.job.data["chat_id"],
            message_id=context.job.data["message_id"],
        )

        try:
            message = await bot.send_voice(
                context.job.data["chat_id"],
                open(destination_path, "rb"),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                t(language).pgettext(
                                    "bot-generic", "Store the voice message"
                                ),
                                callback_data="store_voice",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                t(language).pgettext(
                                    "admin-tours", "Store the original audio"
                                ),
                                callback_data="store_audio_as_is",
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
            context.user_data["voice_file_id"] = message.voice.file_id
        except Exception:
            log.exception(
                "Failed to upload voice message %s", context.user_data["audio_file_id"]
            )
            await bot.edit_message_text(
                t(language).pgettext(
                    "admin-tours",
                    "Something went wrong when I tried to upload the file."
                    " What should I do now?",
                ),
                chat_id=context.job.data["chat_id"],
                message_id=context.job.data["message_id"],
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                t(language).pgettext("bot-generic", "Try again"),
                                callback_data="convert_audio",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                t(language).pgettext(
                                    "admin-tours", "Store the original audio"
                                ),
                                callback_data="store_audio_as_is",
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
            return
        finally:
            os.unlink(destination_path)

        await bot.edit_message_text(
            t(language).pgettext(
                "admin-tours",
                "The audio was converted successfully. Please check the quality"
                " and decide what do you want to do with it.",
            ),
            chat_id=context.job.data["chat_id"],
            message_id=context.job.data["message_id"],
        )

    async def translation_section_content_add_audio_convert(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        language = await self.get_language(update, context)
        context.job_queue.run_once(
            self.convert_audio,
            0,
            data={
                "message_id": update.callback_query.message.id,
                "language": language,
                "chat_id": update.effective_chat.id,
                "user_id": update.effective_user.id,
            },
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id,
        )
        await update.callback_query.answer()
        await self.edit_or_reply_text(
            update,
            context,
            t(language).pgettext(
                "admin-tours", "Starting the audio conversion process..."
            ),
        )
        return self.STATE_TOUR_AUDIO_CONVERT_VOICE_CHECK

    async def translation_section_content_add_store_voice(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        await self.translation_section_content_add(
            context.user_data["audio_message_id"],
            context,
            MessageType.voice,
            file_id=context.user_data["voice_file_id"],
            file_caption=context.user_data["audio_caption"],
        )
        await self._report_voice_saved(update, context)

        return ConversationHandler.END

    async def translation_section_content_add_store_audio(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        await self.translation_section_content_add(
            context.user_data["audio_message_id"],
            context,
            MessageType.audio,
            file_id=context.user_data["audio_file_id"],
            file_caption=context.user_data["audio_caption"],
        )
        await self._report_audio_saved(update, context)

        return ConversationHandler.END

    async def translation_section_content_add_mute_and_store_audio(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        audio_to_voice_state = await Settings.load(
            self.db_session, SettingsKey.audio_to_voice, create=True
        )
        audio_to_voice_state.disable()

        self.db_session.add(audio_to_voice_state)
        await self.db_session.commit()

        await self.translation_section_content_add(
            context.user_data["audio_message_id"],
            context,
            MessageType.audio,
            file_id=context.user_data["audio_file_id"],
            file_caption=context.user_data["audio_caption"],
        )
        await self._report_audio_saved(update, context)

        language = await self.get_language(update, context)
        await self.reply_text(
            update,
            context,
            t(language).pgettext(
                "admin-tours",
                "Audio-to-voice conversion suggestions have been disabled."
                " You can enabled them again using /configure command in the"
                " admin mode.",
            ),
        )

        return ConversationHandler.END

    async def _report_audio_saved(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        language = await self.get_language(update, context)
        message = t(language).pgettext(
            "admin-tours", "The audio was added to the section!"
        )
        message += " "
        message += t(language).pgettext(
            "admin-tours",
            "Add more data or send /done if you're finished with the section.",
        )

        if update.message and update.message.media_group_id:
            message += " "
            message += t(language).pgettext(
                "admin-tours",
                "Please wait until all audios in the group are uploaded before proceeding to the next section.",
            )
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.delete_message()

        await self.reply_text(update, context, message)

    async def translation_section_content_add_audio(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        if not update.message.media_group_id:
            audio_to_voice_state = await Settings.load(
                self.db_session, SettingsKey.audio_to_voice, create=True
            )

            if audio_to_voice_state.is_enabled:
                language = await self.get_language(update, context)
                context.user_data["audio_file_id"] = update.message.audio.file_id
                context.user_data["audio_message_id"] = update.message.message_id
                context.user_data["audio_caption"] = (
                    update.message.caption_markdown_v2_urled
                )

                await update.message.reply_text(
                    t(language).pgettext(
                        "admin-tours",
                        "Would you like to convert this audio file to a voice message?",
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    t(language).pgettext("bot-generic", "Yes"),
                                    callback_data="convert_audio",
                                ),
                                InlineKeyboardButton(
                                    t(language).pgettext("bot-generic", "No"),
                                    callback_data="store_audio_as_is",
                                ),
                            ],
                            [
                                InlineKeyboardButton(
                                    t(language).pgettext(
                                        "admin-tours", "No, and do not ask again."
                                    ),
                                    callback_data="disable_conversion_and_store_audio_as_is",
                                )
                            ],
                        ]
                    ),
                )
                return self.STATE_TOUR_AUDIO_CONVERT_CONFIRMATION

        is_first = await self.translation_section_content_add(
            update.message.message_id,
            context,
            MessageType.audio,
            media_group_id=update.message.media_group_id,
            file_id=update.message.audio.file_id,
            file_caption=update.message.caption_markdown_v2_urled,
        )

        if is_first:
            await self._report_audio_saved(update, context)

        return ConversationHandler.END

    async def translation_section_content_add_video(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        is_first = await self.translation_section_content_add(
            update.message.message_id,
            context,
            MessageType.video,
            media_group_id=update.message.media_group_id,
            file_id=update.message.video.file_id,
            file_caption=update.message.caption_markdown_v2_urled,
        )

        if is_first:
            language = await self.get_language(update, context)
            message = t(language).pgettext(
                "admin-tours", "The video was added to the section!"
            )
            message += " "
            message += t(language).pgettext(
                "admin-tours",
                "Add more data or send /done if you're finished with the section.",
            )

            if update.message.media_group_id:
                message += " "
                message += t(language).pgettext(
                    "admin-tours",
                    "Please wait until all videos in the group are uploaded before proceeding to the next section.",
                )

            await update.message.reply_text(message)

    async def translation_section_content_add_photo(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        sorted_photos = list(
            sorted(
                update.message.photo,
                key=lambda photo: photo["width"] * photo["height"],
                reverse=True,
            )
        )

        is_first = await self.translation_section_content_add(
            update.message.message_id,
            context,
            MessageType.photo,
            media_group_id=update.message.media_group_id,
            file_id=sorted_photos[0].file_id,
            file_caption=update.message.caption_markdown_v2_urled,
        )

        if is_first:
            language = await self.get_language(update, context)
            message = t(language).pgettext(
                "admin-tours", "The photo was added to the section!"
            )
            message += " "
            message += t(language).pgettext(
                "admin-tours",
                "Add more data or send /done if you're finished with the section.",
            )

            if update.message.media_group_id:
                message += " "
                message += t(language).pgettext(
                    "admin-tours",
                    "Please wait until all photos in the group are uploaded before proceeding to the next section.",
                )

            await update.message.reply_text(message)

    async def translation_unknown_content(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        language = (await self.get_user(update, context)).language
        await update.message.reply_text(
            t(language).pgettext(
                "admin-tours",
                "Unsupported message! Please send me one of the"
                " following to add to the tour section: location, text,"
                " photo, audio, video, animation, voice or video note.",
            )
        )
