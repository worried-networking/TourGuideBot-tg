import hashlib
import re

from sqlalchemy import select
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tour_guide_bot import t
from tour_guide_bot.bot.admin.approve import ApproveCommandHandler
from tour_guide_bot.bot.admin.bot_commands import BotCommandsFactory
from tour_guide_bot.bot.admin.configure import ConfigureCommandHandler
from tour_guide_bot.bot.admin.help import HelpCommandHandler
from tour_guide_bot.bot.admin.revoke import RevokeCommandHandler
from tour_guide_bot.bot.admin.tour import TourCommandHandler
from tour_guide_bot.bot.guide.bot_commands import (
    BotCommandsFactory as GuestBotCommandsFactory,
)
from tour_guide_bot.helpers.telegram import BaseHandlerCallback
from tour_guide_bot.models.admin import Admin, AdminPermissions


class StartCommandHandler(BaseHandlerCallback):
    STATE_CONTACT = 1
    STATE_TOKEN = 2
    STATE_ADMIN_MODE_ACTIVE = 3

    @classmethod
    def get_handlers(cls):
        all_admin_handlers = ApproveCommandHandler.get_handlers()
        all_admin_handlers += ConfigureCommandHandler.get_handlers()
        all_admin_handlers += RevokeCommandHandler.get_handlers()
        all_admin_handlers += TourCommandHandler.get_handlers()
        all_admin_handlers += HelpCommandHandler.get_handlers()

        return [
            ConversationHandler(
                entry_points=[CommandHandler("admin", cls.partial(cls.start))],
                states={
                    cls.STATE_CONTACT: [
                        MessageHandler(filters.CONTACT, cls.partial(cls.contact)),
                        CommandHandler(
                            "help",
                            HelpCommandHandler.partial(
                                HelpCommandHandler.waiting_contact_help
                            ),
                        ),
                        CommandHandler("cancel", cls.partial(cls.exit_admin_mode)),
                    ],
                    cls.STATE_TOKEN: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND, cls.partial(cls.token)
                        ),
                        CommandHandler(
                            "help",
                            HelpCommandHandler.partial(
                                HelpCommandHandler.waiting_token_help
                            ),
                        ),
                        CommandHandler("cancel", cls.partial(cls.exit_admin_mode)),
                    ],
                    cls.STATE_ADMIN_MODE_ACTIVE: all_admin_handlers,
                },
                fallbacks=[
                    CommandHandler("guest", cls.partial(cls.exit_admin_mode)),
                    MessageHandler(filters.COMMAND, cls.partial(cls.unknown_command)),
                    MessageHandler(filters.ALL, cls.partial(cls.unexpected_message)),
                ],
                name="admin-init",
                persistent=True,
            )
        ]

    @staticmethod
    def request_contact(language: str):
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        t(language).pgettext("admin-bot-start", "Share phone number"),
                        request_contact=True,
                    )
                ]
            ],
            one_time_keyboard=True,
        )

    async def contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_user(update, context)

        if update.message.contact.user_id != update.message.from_user.id:
            await update.message.reply_text(
                t(user.language).pgettext(
                    "admin-bot-start",
                    "Please send me your contact number and not somebody else's.",
                ),
                reply_markup=self.request_contact(user.language),
            )
            return self.STATE_CONTACT

        user.phone = re.sub(r"\D+", "", update.message.contact.phone_number)

        stmt = select(Admin).where(Admin.phone == user.phone)
        admin: Admin | None = await self.db_session.scalar(stmt)

        if admin:
            user.admin = admin

        self.db_session.add(user)
        await self.db_session.commit()

        if admin:
            await BotCommandsFactory.start(
                update.get_bot(),
                user,
                await self.get_language(update, context),
                self.db_session,
            )

            await update.message.reply_text(
                t(user.language).pgettext(
                    "admin-bot-start",
                    "Admin permissions confirmed! Use /help command if you need further help.",
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
            return self.STATE_ADMIN_MODE_ACTIVE
        else:
            await update.message.reply_text(
                t(user.language).pgettext(
                    "admin-bot-start",
                    "I don't think you're in the right place. Please send me the md5 hash of the token to confirm ownership.",
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
            return self.STATE_TOKEN

    async def token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_user(update, context)

        entered_token = update.message.text.strip()
        md5_bot_token = hashlib.md5(context.application.bot.token.encode()).hexdigest()

        if entered_token == md5_bot_token:
            admin = Admin(phone=user.phone, permissions=AdminPermissions.full)
            user.admin = admin
            self.db_session.add_all([admin, user])
            await self.db_session.commit()

            await BotCommandsFactory.start(
                update.get_bot(),
                user,
                await self.get_language(update, context),
                self.db_session,
            )

            await update.message.reply_text(
                t(user.language).pgettext(
                    "admin-bot-start",
                    "Admin permissions confirmed! Use /help command if you need further help.",
                )
            )
            return self.STATE_ADMIN_MODE_ACTIVE
        else:
            await update.message.reply_text(
                t(user.language).pgettext(
                    "admin-bot-start",
                    "I still don't recognize you, sorry. Try saying /admin again when you're ready.",
                )
            )

            return ConversationHandler.END

    async def exit_admin_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_user(update, context)
        await GuestBotCommandsFactory.start(
            update.get_bot(),
            user,
            await self.get_language(update, context),
            self.db_session,
        )

        await update.message.reply_text(
            t(user.language).pgettext(
                "admin-bot-start", "You're in guest mode now, bye!"
            )
        )
        return ConversationHandler.END

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_user(update, context)

        if user.admin:
            await BotCommandsFactory.start(
                update.get_bot(),
                user,
                await self.get_language(update, context),
                self.db_session,
            )

            await update.message.reply_text(
                t(user.language).pgettext(
                    "admin-bot-start", "Welcome to the admin mode!"
                )
            )
            return self.STATE_ADMIN_MODE_ACTIVE
        elif not user.phone:
            await update.message.reply_text(
                t(user.language).pgettext(
                    "admin-bot-start",
                    "I don't recognize you! Please send me your phone number.",
                ),
                reply_markup=self.request_contact(user.language),
            )
            return self.STATE_CONTACT
        else:
            stmt = select(Admin).where(Admin.phone == user.phone)
            admin: Admin | None = await self.db_session.scalar(stmt)

            if admin:
                user.admin = admin
                self.db_session.add(user)
                await self.db_session.commit()
                await BotCommandsFactory.start(
                    update.get_bot(),
                    user,
                    await self.get_language(update, context),
                    self.db_session,
                )

                await update.message.reply_text(
                    t(user.language).pgettext(
                        "admin-bot-start", "Welcome to the admin mode!"
                    )
                )
                return self.STATE_ADMIN_MODE_ACTIVE
            else:
                await update.message.reply_text(
                    t(user.language).pgettext(
                        "admin-bot-start",
                        "I don't think you're in the right place. Please send me the md5 hash of the token to confirm ownership.",
                    )
                )
                return self.STATE_TOKEN
