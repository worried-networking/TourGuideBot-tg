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


class ProtectContent(SubcommandHandler):
    STATE_PROTECT_CONTENT = 1

    @staticmethod
    def get_name(language: str) -> str:
        return t(language).pgettext("admin-configure", "Content protection")

    @classmethod
    def get_handlers(cls):
        return [
            ConversationHandler(
                entry_points=[
                    CallbackQueryHandler(
                        cls.partial(cls.change_protect_content_init),
                        cls.get_callback_data_pattern(),
                    ),
                ],
                states={
                    cls.STATE_PROTECT_CONTENT: [
                        CallbackQueryHandler(
                            cls.partial(cls.change_protect_content),
                            "^protect_content:(enable|disable)$",
                        ),
                    ],
                },
                fallbacks=[
                    CommandHandler("cancel", cls.partial(cls.cancel)),
                    CallbackQueryHandler(cls.partial(cls.cancel), "cancel"),
                    MessageHandler(filters.COMMAND, cls.partial(cls.unknown_command)),
                    MessageHandler(filters.ALL, cls.partial(cls.unexpected_message)),
                ],
                name="admin-configure-protect-content",
                persistent=True,
            )
        ]

    async def change_protect_content_init(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        language = await self.get_language(update, context)
        protect_content_state = await Settings.load(
            self.db_session, SettingsKey.protect_content, create=True
        )

        await update.callback_query.answer()
        if protect_content_state.is_enabled:
            await update.callback_query.edit_message_text(
                t(language).pgettext(
                    "admin-configure",
                    r"Content protection is currently *enabled*\. Guests can neither forward nor save tour content \(and, in some Telegram apps, take screenshots of it\)\. The change applies only to messages sent from now on\. Would you like to disable it?",
                ),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                t(language).pgettext("bot-generic", "Yes"),
                                callback_data="protect_content:disable",
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
                    r"Content protection is currently *disabled*\. Guests can forward and save tour content \(and take screenshots of it\)\. Enabling it prevents this, but applies only to messages sent from now on\. Would you like to enable it?",
                ),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                t(language).pgettext("bot-generic", "Yes"),
                                callback_data="protect_content:enable",
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

        return self.STATE_PROTECT_CONTENT

    async def change_protect_content(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        language = await self.get_language(update, context)
        protect_content_state = await Settings.load(
            self.db_session, SettingsKey.protect_content, create=True
        )
        if context.matches[0].group(1) == "enable":
            protect_content_state.enable()
        else:
            protect_content_state.disable()

        self.db_session.add(protect_content_state)
        await self.db_session.commit()

        await update.callback_query.answer()
        if context.matches[0].group(1) == "enable":
            await update.callback_query.edit_message_text(
                t(language).pgettext(
                    "admin-configure",
                    "Content protection was enabled.",
                )
            )
        else:
            await update.callback_query.edit_message_text(
                t(language).pgettext(
                    "admin-configure",
                    "Content protection was disabled.",
                )
            )

        return ConversationHandler.END
