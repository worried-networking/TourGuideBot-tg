from telegram.ext import CommandHandler

from tour_guide_bot import t
from tour_guide_bot.bot.admin.configure.audio_to_voice import AudioToVoice
from tour_guide_bot.bot.admin.configure.delay_between_messages import (
    DelayBetweenMessages,
)
from tour_guide_bot.bot.admin.configure.messages.support import SupportMessage
from tour_guide_bot.bot.admin.configure.messages.terms import TermsMessage
from tour_guide_bot.bot.admin.configure.messages.welcome import WelcomeMessage
from tour_guide_bot.bot.admin.configure.payments import PaymentsSubcommand
from tour_guide_bot.bot.admin.configure.protect_content import ProtectContent
from tour_guide_bot.helpers.telegram import MenuCommandHandler


class ConfigureCommandHandler(MenuCommandHandler):
    MENU_ITEMS = [
        WelcomeMessage,
        TermsMessage,
        SupportMessage,
        PaymentsSubcommand,
        AudioToVoice,
        ProtectContent,
        DelayBetweenMessages,
    ]

    @classmethod
    def get_main_handlers(cls) -> list[CommandHandler]:
        return [CommandHandler("configure", cls.partial(cls.main_entrypoint))]

    def get_main_menu_text(self, language: str) -> str:
        return t(language).pgettext(
            "admin-configure", "Please select the parameter you want to change."
        )
