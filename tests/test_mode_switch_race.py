import asyncio

import pytest
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation

from tour_guide_bot.bot.admin.bot_commands import BotCommandsFactory as AdminCommands
from tour_guide_bot.bot.guide.bot_commands import BotCommandsFactory as GuideCommands

from .conftest import get_phone_number_request

# Long enough for the next message to reach the bot while set_my_commands is
# still running, short enough to leave room in the 10s conversation timeout.
SLOW = 2
# The user may see a reply before the bot's sendMessage call returns, so the
# state can only be expected to be stored after a short, human-like pause.
REACTION = 0.5


def slow_start(mocker, factory):
    original = factory.start

    async def wrapper(*args, **kwargs):
        await asyncio.sleep(SLOW)
        return await original(*args, **kwargs)

    mocker.patch.object(factory, "start", new=wrapper)


@pytest.mark.usefixtures("app", "admin")
@pytest.mark.enabled_languages("en")
async def test_command_right_after_admin_welcome_is_handled_in_admin_mode(
    conversation: Conversation, mocker
):
    """The state must be stored before the user can see the reply, even if set_my_commands is slow."""
    slow_start(mocker, AdminCommands)

    await conversation.send_message("/admin")
    response: Message = await conversation.get_response()
    assert "Welcome to the admin mode" in response.message, (
        "Unexpected message in response to the admin mode switch"
    )

    await asyncio.sleep(REACTION)
    await conversation.send_message("/configure")
    response = await conversation.get_response()
    assert "Please select the parameter you want to change" in response.message, (
        "/configure sent right after the welcome message was not handled in admin mode"
    )


@pytest.mark.usefixtures("app")
async def test_command_right_after_guest_auth_reply_is_handled_as_guest(
    conversation: Conversation, mocker
):
    """The conversation must end before the user can see the reply, even if set_my_commands is slow."""
    slow_start(mocker, GuideCommands)

    await conversation.send_message("/start")
    response: Message = await conversation.get_response()
    assert response.message == "welcome (en)", "Unexpected first message"

    response = await get_phone_number_request(conversation)
    await response.click(0, share_phone=True)

    response = await conversation.get_response()
    assert (
        "Unfortunately, no tours are available for you at the moment"
        in response.message
    ), "Unexpected response to a user without tours"

    await asyncio.sleep(REACTION)
    await conversation.send_message("/tours")
    response = await conversation.get_response()
    assert "Unknown command" not in response.message, (
        "/tours sent right after the auth reply hit the contact-state fallback"
    )
    assert (
        "Unfortunately, no tours are available for you at the moment"
        in response.message
    ), "Unexpected response to /tours"
