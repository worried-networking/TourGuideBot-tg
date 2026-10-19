import aiohttp_jinja2
from aiohttp.web import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tour_guide_bot import t
from tour_guide_bot.models.settings import Settings, SettingsKey
from tour_guide_bot.web.admin.base import Base


class Configuration(Base):
    @aiohttp_jinja2.template("admin/configuration.html")
    async def get(self, request: Request):
        await self.auth(request)

        async with AsyncSession(request.app.db_engine) as db_session:
            all_settings = await db_session.scalars(select(Settings))

            all_settings = {
                f"{setting.key.name}-{setting.language}".replace(
                    "-None", ""
                ): setting.value
                for setting in all_settings
            }

        if SettingsKey.audio_to_voice.name not in all_settings:
            all_settings[SettingsKey.audio_to_voice.name] = Settings.DEFAULT_VALUES[
                SettingsKey.audio_to_voice
            ]

        if SettingsKey.protect_content.name not in all_settings:
            all_settings[SettingsKey.protect_content.name] = Settings.DEFAULT_VALUES[
                SettingsKey.protect_content
            ]

        if SettingsKey.delay_between_messages.name not in all_settings:
            all_settings[
                SettingsKey.delay_between_messages.name
            ] = Settings.DEFAULT_VALUES[SettingsKey.delay_between_messages]

        return {
            "settings": all_settings,
            "message_types": {
                SettingsKey.guide_welcome_message.name: t().pgettext(
                    "admin-configure", "Guide welcome message"
                ),
                SettingsKey.support_message.name: t().pgettext(
                    "admin-configure", "Support message"
                ),
                SettingsKey.terms_message.name: t().pgettext(
                    "admin-configure", "Terms & Conditions"
                ),
            },
        }
