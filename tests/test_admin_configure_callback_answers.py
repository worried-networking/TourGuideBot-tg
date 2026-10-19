import pytest
from telethon.events import MessageEdited
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation
from telethon.tl.types.messages import BotCallbackAnswer


async def _open_configure_item(conversation: Conversation, item: str) -> Message:
    await conversation.send_message("/configure")
    response: Message = await conversation.get_response()

    assert (
        "Please select the parameter you want to change" in response.message
    ), "Unexpected message in response to /configure"

    response = await response.click(text=item)
    assert isinstance(
        response, BotCallbackAnswer
    ), "BotCallbackAnswer didn't arrive after the inline button click"

    event: MessageEdited.Event = await conversation.wait_event(MessageEdited())
    return event.message


@pytest.mark.usefixtures("app")
@pytest.mark.enabled_languages("en")
async def test_audio_to_voice_buttons_are_answered(admin_conversation: Conversation):
    msg = await _open_configure_item(admin_conversation, "Audio-to-voice suggestions")
    assert (
        "currently" in msg.message and "enabled" in msg.message
    ), "Unexpected audio-to-voice state in the prompt"

    response = await msg.click(text="Yes")
    assert isinstance(
        response, BotCallbackAnswer
    ), "BotCallbackAnswer didn't arrive after the inline button click"

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    assert "were disabled" in event.message.message


@pytest.mark.usefixtures("app")
@pytest.mark.enabled_languages("en")
async def test_delay_between_messages_button_is_answered(
    admin_conversation: Conversation,
):
    msg = await _open_configure_item(admin_conversation, "Delay between messages")
    assert "delay between messages" in msg.message
