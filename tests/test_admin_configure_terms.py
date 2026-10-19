import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from telethon.events import MessageEdited
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation
from telethon.tl.types.messages import BotCallbackAnswer

from tour_guide_bot.models.settings import Settings, SettingsKey


@pytest.mark.usefixtures("app", "guest")
@pytest.mark.enabled_languages("en")
async def test_change_terms_message_single_language(
    admin_conversation: Conversation, db_engine: AsyncEngine
):
    conversation = admin_conversation
    await conversation.send_message("/configure")
    response: Message = await conversation.get_response()

    assert "Please select the parameter you want to change" in response.message, (
        "Unexpected message in response to /configure"
    )

    response = await response.click(text="Terms & Conditions")
    assert isinstance(response, BotCallbackAnswer), (
        "BotCallbackAnswer didn't arrive after the inline button click"
    )

    event: MessageEdited.Event = await conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "The bot currently has the following terms & conditions" in msg.message, (
        "Unexpected message after selecting the message type"
    )

    current_terms_message: Message = await conversation.get_response()

    assert current_terms_message.message == "terms (en)", (
        "Unexpected old t&cs message message"
    )

    await conversation.send_message("new terms & conditions")
    response = await conversation.get_response()

    assert "terms & conditions has been changed" in response.message, (
        "Unexpected response to terms & conditions update"
    )

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        terms = await Settings.load(session, SettingsKey.terms_message, "en")
        assert terms is not None

        assert terms.value == "new terms & conditions", (
            "Unexpected new terms & conditions in the default language"
        )

        terms_ru = await Settings.load(session, SettingsKey.terms_message, "ru")
        assert terms_ru is None


@pytest.mark.usefixtures("unconfigured_app", "guest")
@pytest.mark.enabled_languages("en")
async def test_set_terms_message_single_language(
    admin_conversation: Conversation, db_engine: AsyncEngine
):
    conversation = admin_conversation
    await conversation.send_message("/configure")
    response: Message = await conversation.get_response()

    assert "Please select the parameter you want to change" in response.message, (
        "Unexpected message in response to /configure"
    )

    response = await response.click(text="Terms & Conditions")
    assert isinstance(response, BotCallbackAnswer), (
        "BotCallbackAnswer didn't arrive after the inline button click"
    )

    event: MessageEdited.Event = await conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "doesn't have a terms & conditions" in msg.message, (
        "Unexpected message after selecting the message type"
    )

    await conversation.send_message("new terms & conditions")
    response = await conversation.get_response()

    assert "terms & conditions has been changed" in response.message, (
        "Unexpected response to terms & conditions update"
    )

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        terms = await Settings.load(session, SettingsKey.terms_message, "en")
        assert terms is not None

        assert terms.value == "new terms & conditions", (
            "Unexpected new terms & conditions in the default language"
        )

        terms_ru = await Settings.load(session, SettingsKey.terms_message, "ru")
        assert terms_ru is None


@pytest.mark.usefixtures("unconfigured_app", "guest")
@pytest.mark.enabled_languages("en", "ru")
async def test_set_terms_message_multiple_language(
    admin_conversation: Conversation, db_engine: AsyncEngine
):
    conversation = admin_conversation
    await conversation.send_message("/configure")
    response: Message = await conversation.get_response()

    assert "Please select the parameter you want to change" in response.message, (
        "Unexpected message in response to /configure"
    )

    response = await response.click(text="Terms & Conditions")
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

    assert "doesn't have a terms & conditions" in msg.message, (
        "Unexpected message after selecting the language"
    )

    await conversation.send_message("new terms & conditions")
    response: Message = await conversation.get_response()

    assert "terms & conditions has been changed" in response.message, (
        "Unexpected response to terms & conditions update"
    )

    await conversation.send_message("/configure")
    response: Message = await conversation.get_response()

    assert "Please select the parameter you want to change" in response.message, (
        "Unexpected message in response to /configure"
    )

    response = await response.click(text="Terms & Conditions")
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

    assert "doesn't have a terms & conditions" in msg.message, (
        "Unexpected message after selecting the language"
    )

    await conversation.send_message("new terms & conditions (ru)")
    response: Message = await conversation.get_response()

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        terms = await Settings.load(session, SettingsKey.terms_message, "en")
        assert terms is not None

        assert terms.value == "new terms & conditions", (
            "Unexpected new terms & conditions in the default language"
        )

        terms_ru = await Settings.load(session, SettingsKey.terms_message, "ru")

        assert terms_ru is not None
        assert terms_ru.value == r"new terms & conditions \(ru\)", (
            "Unexpected new terms & conditions in the default language"
        )
