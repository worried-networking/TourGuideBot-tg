import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from telethon.events import MessageEdited
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation
from telethon.tl.types.messages import BotCallbackAnswer

from tour_guide_bot.models.settings import Settings, SettingsKey


@pytest.mark.usefixtures("app", "guest")
@pytest.mark.enabled_languages("en")
async def test_change_support_message_single_language(
    admin_conversation: Conversation, db_engine: AsyncEngine
):
    conversation = admin_conversation
    await conversation.send_message("/configure")
    response: Message = await conversation.get_response()

    assert "Please select the parameter you want to change" in response.message, (
        "Unexpected message in response to /configure"
    )

    response = await response.click(text="Support message")
    assert isinstance(response, BotCallbackAnswer), (
        "BotCallbackAnswer didn't arrive after the inline button click"
    )

    event: MessageEdited.Event = await conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "The bot currently has the following support message" in msg.message, (
        "Unexpected message after selecting the message type"
    )

    current_support_message: Message = await conversation.get_response()

    assert current_support_message.message == "support (en)", (
        "Unexpected old support message"
    )

    await conversation.send_message("new support message")
    response = await conversation.get_response()

    assert "support message has been changed" in response.message, (
        "Unexpected response to support message update"
    )

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        support = await Settings.load(session, SettingsKey.support_message, "en")
        assert support is not None

        assert support.value == "new support message", (
            "Unexpected new support message in the default language"
        )

        support_ru = await Settings.load(session, SettingsKey.support_message, "ru")
        assert support_ru is None


@pytest.mark.usefixtures("unconfigured_app", "guest")
@pytest.mark.enabled_languages("en")
async def test_set_support_message_single_language(
    admin_conversation: Conversation, db_engine: AsyncEngine
):
    conversation = admin_conversation
    await conversation.send_message("/configure")
    response: Message = await conversation.get_response()

    assert "Please select the parameter you want to change" in response.message, (
        "Unexpected message in response to /configure"
    )

    response = await response.click(text="Support message")
    assert isinstance(response, BotCallbackAnswer), (
        "BotCallbackAnswer didn't arrive after the inline button click"
    )

    event: MessageEdited.Event = await conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "doesn't have a support message" in msg.message, (
        "Unexpected message after selecting the message type"
    )

    await conversation.send_message("new support message")
    response = await conversation.get_response()

    assert "support message has been changed" in response.message, (
        "Unexpected response to support message update"
    )

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        support = await Settings.load(session, SettingsKey.support_message, "en")
        assert support is not None

        assert support.value == "new support message", (
            "Unexpected new support message in the default language"
        )

        support_ru = await Settings.load(session, SettingsKey.support_message, "ru")
        assert support_ru is None


@pytest.mark.usefixtures("unconfigured_app", "guest")
@pytest.mark.enabled_languages("en", "ru")
async def test_set_support_message_multiple_language(
    admin_conversation: Conversation, db_engine: AsyncEngine
):
    conversation = admin_conversation
    await conversation.send_message("/configure")
    response: Message = await conversation.get_response()

    assert "Please select the parameter you want to change" in response.message, (
        "Unexpected message in response to /configure"
    )

    response = await response.click(text="Support message")
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

    assert "doesn't have a support message" in msg.message, (
        "Unexpected message after selecting the language"
    )

    await conversation.send_message("new support message")
    response: Message = await conversation.get_response()

    assert "support message has been changed" in response.message, (
        "Unexpected response to support message update"
    )

    await conversation.send_message("/configure")
    response: Message = await conversation.get_response()

    assert "Please select the parameter you want to change" in response.message, (
        "Unexpected message in response to /configure"
    )

    response = await response.click(text="Support message")
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

    assert "doesn't have a support message" in msg.message, (
        "Unexpected message after selecting the language"
    )

    await conversation.send_message("new support message (ru)")
    response: Message = await conversation.get_response()

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        support = await Settings.load(session, SettingsKey.support_message, "en")
        assert support is not None

        assert support.value == "new support message", (
            "Unexpected new support message in the default language"
        )

        support_ru = await Settings.load(session, SettingsKey.support_message, "ru")

        assert support_ru is not None
        assert support_ru.value == r"new support message \(ru\)", (
            "Unexpected new support message in the default language"
        )
