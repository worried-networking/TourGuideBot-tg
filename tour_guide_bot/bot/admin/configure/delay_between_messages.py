from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tour_guide_bot import t
from tour_guide_bot.helpers.telegram import SubcommandHandler
from tour_guide_bot.models.settings import Settings, SettingsKey


class DelayBetweenMessages(SubcommandHandler):
    STATE_DELAY_BETWEEN_MESSAGES = 1

    @staticmethod
    def get_name(language: str) -> str:
        return t(language).pgettext("admin-configure", "Delay between messages")

    @classmethod
    def get_handlers(cls):
        return [
            ConversationHandler(
                entry_points=[
                    CallbackQueryHandler(
                        cls.partial(cls.change_delay_between_messages_init),
                        cls.get_callback_data_pattern(),
                    )
                ],
                states={
                    cls.STATE_DELAY_BETWEEN_MESSAGES: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND,
                            cls.partial(cls.change_delay_between_messages),
                        ),
                    ],
                },
                fallbacks=[
                    CommandHandler("cancel", cls.partial(cls.cancel)),
                    CallbackQueryHandler(cls.partial(cls.cancel), "cancel"),
                    MessageHandler(filters.COMMAND, cls.partial(cls.unknown_command)),
                    MessageHandler(filters.ALL, cls.partial(cls.unexpected_message)),
                ],
                name="admin-configure-delay-between-messages",
                persistent=True,
            )
        ]

    async def change_delay_between_messages_init(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        language = await self.get_language(update, context)
        delay_between_messages_state = await Settings.load(
            self.db_session, SettingsKey.delay_between_messages, create=True
        )

        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            t(language).pgettext(
                "admin-configure",
                "Current delay between messages is %0.1fs. "
                "Please enter a desired delay (float value between 0 and 4.5).",
            )
            % (float(delay_between_messages_state.value)),
        )

        return self.STATE_DELAY_BETWEEN_MESSAGES

    async def change_delay_between_messages(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        language = await self.get_language(update, context)

        try:
            delay = float(update.message.text)
        except ValueError:
            await update.message.reply_text(
                t(language).pgettext(
                    "admin-configure",
                    "Please enter a float value between 0 and 4.5.",
                )
            )
            return

        if not 0 <= delay <= 4.5:
            await update.message.reply_text(
                t(language).pgettext(
                    "admin-configure",
                    "Please enter a float value between 0 and 4.5.",
                )
            )
            return

        delay_between_messages_state = await Settings.load(
            self.db_session, SettingsKey.delay_between_messages, create=True
        )
        delay_between_messages_state.value = delay
        self.db_session.add(delay_between_messages_state)
        await self.db_session.commit()

        await update.message.reply_text(
            t(language).pgettext(
                "admin-configure",
                "The delay was updated!",
            )
        )

        return ConversationHandler.END
