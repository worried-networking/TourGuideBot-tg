from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tour_guide_bot import t
from tour_guide_bot.helpers.telegram import (
    SubcommandHandler,
)
from tour_guide_bot.models.settings import Settings, SettingsKey


class AudioToVoice(SubcommandHandler):
    STATE_AUDIO_TO_VOICE = 1

    @staticmethod
    def get_name(language: str) -> str:
        return t(language).pgettext("admin-configure", "Audio-to-voice suggestions")

    @classmethod
    def get_handlers(cls):
        return [
            ConversationHandler(
                entry_points=[
                    CallbackQueryHandler(
                        cls.partial(cls.change_audio_to_voice_init),
                        cls.get_callback_data_pattern(),
                    ),
                ],
                states={
                    cls.STATE_AUDIO_TO_VOICE: [
                        CallbackQueryHandler(
                            cls.partial(cls.change_audio_to_voice),
                            "^audio_to_voice:(enable|disable)$",
                        ),
                    ],
                },
                fallbacks=[
                    CommandHandler("cancel", cls.partial(cls.cancel)),
                    CallbackQueryHandler(cls.partial(cls.cancel), "cancel"),
                    MessageHandler(filters.COMMAND, cls.partial(cls.unknown_command)),
                    MessageHandler(filters.ALL, cls.partial(cls.unexpected_message)),
                ],
                name="admin-configure-audio-to-voice",
                persistent=True,
            )
        ]

    async def change_audio_to_voice_init(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        language = await self.get_language(update, context)
        audio_to_voice_state = await Settings.load(
            self.db_session, SettingsKey.audio_to_voice, create=True
        )

        await update.callback_query.answer()
        if audio_to_voice_state.is_enabled:
            await update.callback_query.edit_message_text(
                t(language).pgettext(
                    "admin-configure",
                    r"Audio\-to\-voice conversion suggestions are currently *enabled*\. Would you like to disable them?",
                ),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                t(language).pgettext("bot-generic", "Yes"),
                                callback_data="audio_to_voice:disable",
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
        else:
            await update.callback_query.edit_message_text(
                t(language).pgettext(
                    "admin-configure",
                    r"Audio\-to\-voice conversion suggestions are currently *disabled*\. Would you like to enable them?",
                ),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                t(language).pgettext("bot-generic", "Yes"),
                                callback_data="audio_to_voice:enable",
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

        return self.STATE_AUDIO_TO_VOICE

    async def change_audio_to_voice(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        language = await self.get_language(update, context)
        audio_to_voice_state = await Settings.load(
            self.db_session, SettingsKey.audio_to_voice, create=True
        )
        if context.matches[0].group(1) == "enable":
            audio_to_voice_state.enable()
        else:
            audio_to_voice_state.disable()

        self.db_session.add(audio_to_voice_state)
        await self.db_session.commit()

        await update.callback_query.answer()
        if context.matches[0].group(1) == "enable":
            await update.callback_query.edit_message_text(
                t(language).pgettext(
                    "admin-configure",
                    "Audio-to-voice conversion suggestions were enabled.",
                )
            )
        else:
            await update.callback_query.edit_message_text(
                t(language).pgettext(
                    "admin-configure",
                    "Audio-to-voice conversion suggestions were disabled.",
                )
            )

        return ConversationHandler.END
