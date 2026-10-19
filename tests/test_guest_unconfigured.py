import pytest
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation


@pytest.mark.usefixtures("unconfigured_app")
async def test_start_to_unconfigured_bot(conversation: Conversation):
    await conversation.send_message("/start")
    response: Message = await conversation.get_response()
    assert "The bot is not configured yet" in response.message, (
        "Unexpected response from an unconfigured bot"
    )


@pytest.mark.usefixtures("unconfigured_app")
async def test_tours_to_unconfigured_bot(conversation: Conversation):
    await conversation.send_message("/tours")
    response: Message = await conversation.get_response()
    assert "no tours are available for you" in response.message, (
        "Unexpected response from an unconfigured bot"
    )
