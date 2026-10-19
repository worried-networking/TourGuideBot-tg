import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from telethon.events import MessageEdited
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation
from telethon.tl.types.messages import BotCallbackAnswer

from tour_guide_bot.models.settings import Settings, SettingsKey


async def _toggle_protect_content(
    conversation: Conversation, expected_state: str, expected_result: str
):
    await conversation.send_message("/configure")
    response: Message = await conversation.get_response()

    assert (
        "Please select the parameter you want to change" in response.message
    ), "Unexpected message in response to /configure"

    response = await response.click(text="Content protection")
    assert isinstance(
        response, BotCallbackAnswer
    ), "BotCallbackAnswer didn't arrive after the inline button click"

    event: MessageEdited.Event = await conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert (
        "currently" in msg.message and expected_state in msg.message
    ), "Unexpected content protection state in the prompt"

    response = await msg.click(text="Yes")
    assert isinstance(
        response, BotCallbackAnswer
    ), "BotCallbackAnswer didn't arrive after the inline button click"

    event: MessageEdited.Event = await conversation.wait_event(MessageEdited())
    msg = event.message

    assert (
        expected_result in msg.message
    ), "Unexpected message after changing the content protection"


@pytest.mark.usefixtures("app", "guest")
@pytest.mark.enabled_languages("en")
async def test_toggle_protect_content(
    admin_conversation: Conversation, db_engine: AsyncEngine
):
    # Content protection is enabled by default, so the first switch disables it
    await _toggle_protect_content(
        admin_conversation, "enabled", "Content protection was disabled"
    )

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        setting = await Settings.load(session, SettingsKey.protect_content)
        assert setting is not None, "protect_content wasn't saved to the DB"
        assert (
            not setting.is_enabled
        ), "Content protection must be disabled in the DB after the first switch"

    await _toggle_protect_content(
        admin_conversation, "disabled", "Content protection was enabled"
    )

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        setting = await Settings.load(session, SettingsKey.protect_content)
        assert setting is not None, "protect_content disappeared from the DB"
        assert (
            setting.is_enabled
        ), "Content protection must be enabled in the DB after the second switch"
