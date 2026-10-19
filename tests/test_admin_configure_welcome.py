import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from telethon.events import MessageEdited
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation
from telethon.tl.types.messages import BotCallbackAnswer

from tour_guide_bot.models.settings import Settings, SettingsKey


@pytest.mark.usefixtures("app", "guest")
@pytest.mark.enabled_languages("en")
async def test_change_welcome_message_single_language(
    admin_conversation: Conversation, db_engine: AsyncEngine
):
    conversation = admin_conversation
    await conversation.send_message("/configure")
    response: Message = await conversation.get_response()

    assert "Please select the parameter you want to change" in response.message, (
        "Unexpected message in response to /configure"
    )

    response = await response.click(text="Guide welcome message")
    assert isinstance(response, BotCallbackAnswer), (
        "BotCallbackAnswer didn't arrive after the inline button click"
    )

    event: MessageEdited.Event = await conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "The bot currently has the following welcome message" in msg.message, (
        "Unexpected message after selecting the language"
    )

    current_welcome_message: Message = await conversation.get_response()

    assert current_welcome_message.message == "welcome (en)", (
        "Unexpected old welcome message"
    )

    await conversation.send_message("new welcome message")
    response = await conversation.get_response()

    assert "welcome message has been changed" in response.message, (
        "Unexpected response to welcome message update"
    )

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        stmt = select(Settings).where(
            (Settings.key == SettingsKey.guide_welcome_message)
            & (Settings.language == "en")
        )
        welcome_en: Settings | None = await session.scalar(stmt)

        assert welcome_en.value == "new welcome message", (
            "Unexpected new welcome message in the default language"
        )

        stmt = select(Settings).where(
            (Settings.key == SettingsKey.guide_welcome_message)
            & (Settings.language == "ru")
        )
        welcome_ru: Settings | None = await session.scalar(stmt)

        assert welcome_ru is None


@pytest.mark.usefixtures("app", "guest")
@pytest.mark.enabled_languages("en", "ru")
async def test_change_welcome_message_multiple_language(
    admin_conversation: Conversation, db_engine: AsyncEngine
):
    conversation = admin_conversation
    await conversation.send_message("/configure")
    response: Message = await conversation.get_response()

    assert "Please select the parameter you want to change" in response.message, (
        "Unexpected message in response to /configure"
    )

    response = await response.click(text="Guide welcome message")
    assert isinstance(response, BotCallbackAnswer), (
        "BotCallbackAnswer didn't arrive after the inline button click"
    )

    event: MessageEdited.Event = await conversation.wait_event(MessageEdited())
    msg: Message = event.message

    response = await msg.click(text="English")
    assert isinstance(response, BotCallbackAnswer), (
        "BotCallbackAnswer didn't arrive after the inline button click"
    )

    event: MessageEdited.Event = await conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "The bot currently has the following welcome message" in msg.message, (
        "Unexpected message after selecting the language"
    )

    current_welcome_message: Message = await conversation.get_response()

    assert current_welcome_message.message == "welcome (en)", (
        "Unexpected old welcome message"
    )

    await conversation.send_message("new welcome message")
    response: Message = await conversation.get_response()

    assert "welcome message has been changed" in response.message, (
        "Unexpected response to welcome message update"
    )

    await conversation.send_message("/configure")
    response: Message = await conversation.get_response()

    assert "Please select the parameter you want to change" in response.message, (
        "Unexpected message in response to /configure"
    )

    response = await response.click(text="Guide welcome message")
    assert isinstance(response, BotCallbackAnswer), (
        "BotCallbackAnswer didn't arrive after the inline button click"
    )

    event: MessageEdited.Event = await conversation.wait_event(MessageEdited())
    msg: Message = event.message

    response = await msg.click(text="Russian")
    assert isinstance(response, BotCallbackAnswer), (
        "BotCallbackAnswer didn't arrive after the inline button click"
    )

    event: MessageEdited.Event = await conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "The bot currently has the following welcome message" in msg.message, (
        "Unexpected message after selecting the language"
    )

    current_welcome_message: Message = await conversation.get_response()

    assert current_welcome_message.message == "welcome (ru)", (
        "Unexpected old welcome message"
    )

    await conversation.send_message("new welcome message (ru)")
    response: Message = await conversation.get_response()

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        stmt = select(Settings).where(
            (Settings.key == SettingsKey.guide_welcome_message)
            & (Settings.language == "en")
        )
        welcome_en: Settings | None = await session.scalar(stmt)

        assert welcome_en is not None
        assert welcome_en.value == "new welcome message", (
            "Unexpected new welcome message in the default language"
        )

        stmt = select(Settings).where(
            (Settings.key == SettingsKey.guide_welcome_message)
            & (Settings.language == "ru")
        )
        welcome_ru: Settings | None = await session.scalar(stmt)

        assert welcome_ru is not None
        assert welcome_ru.value == r"new welcome message \(ru\)", (
            "Unexpected new welcome message in the second language"
        )
