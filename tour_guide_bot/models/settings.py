import enum
from typing import ClassVar, Optional, Sequence

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped

from tour_guide_bot.models import Base


class SettingsKey(enum.Enum):
    guide_welcome_message = 1
    audio_to_voice = 2
    delay_between_messages = 3
    support_message = 4
    terms_message = 5
    protect_content = 6


class Settings(Base):
    __tablename__ = "settings"
    __mapper_args__ = {"eager_defaults": True}

    __bool_settings = [SettingsKey.audio_to_voice, SettingsKey.protect_content]

    # Global default is None
    DEFAULT_VALUES: ClassVar[dict[SettingsKey, str]] = {
        SettingsKey.delay_between_messages: "4",
        SettingsKey.audio_to_voice: "yes",
        SettingsKey.protect_content: "yes",
    }

    id: Mapped[int] = Column(Integer, primary_key=True)
    key: Mapped[str] = Column(Enum(SettingsKey), nullable=False)
    language: Mapped[Optional[str]] = Column(String)
    value: Mapped[str] = Column(Text, nullable=False)
    created_ts = Column(DateTime, nullable=False, server_default=func.now())
    updated_ts = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_settings_key_language", "key", "language", unique=True),
    )

    @property
    def is_enabled(self) -> bool:
        if self.key not in self.__bool_settings:
            raise RuntimeError("This setting is not boolean")

        return self.value == "yes" or self.value is None

    def enable(self) -> "Settings":
        if self.key not in self.__bool_settings:
            raise RuntimeError("This setting is not boolean")

        self.value = "yes"

        return self

    def disable(self) -> "Settings":
        if self.key not in self.__bool_settings:
            raise RuntimeError("This setting is not boolean")

        self.value = "no"

        return self

    @staticmethod
    async def load(
        db_session: AsyncSession,
        key: SettingsKey,
        language: str | None = None,
        create: bool = False,
    ) -> "Settings":
        stmt = select(Settings).where(
            (Settings.key == key) & (Settings.language == language)
        )
        setting: Settings | None = await db_session.scalar(stmt)
        if not setting and create:
            setting = Settings(
                key=key, language=language, value=Settings.DEFAULT_VALUES.get(key)
            )

        return setting

    @staticmethod
    async def exists(
        db_session: AsyncSession, keys: list[SettingsKey], language: str | None = None
    ) -> bool:
        if language:
            stmt = select(Settings).where(
                Settings.key.in_(keys) & (Settings.language == language)
            )
        else:
            stmt = select(Settings).where(Settings.key.in_(keys))

        stmt = stmt.with_only_columns(Settings.key)

        existing_keys: Sequence[str] = (await db_session.scalars(stmt)).all()

        return len(set(existing_keys)) == len(set(keys))


class PaymentProvider(Base):
    __tablename__ = "payment_provider"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String, nullable=False)
    language: Mapped[Optional[str]] = Column(String)
    enabled: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    config: Mapped[dict] = Column(JSON, nullable=False)
    created_ts = Column(DateTime, nullable=False, server_default=func.now())
    updated_ts = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_payment_provider_language_enabled", "language", "enabled"),
    )
