import pytest
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation


@pytest.mark.usefixtures("app", "guest")
async def test_bot_recognise_added_user(conversation: Conversation):
    await conversation.send_message("/start")
    response: Message = await conversation.get_response()
    assert response.message == "welcome (en)", (
        "Unexpected first message from a configured bot"
    )

    response: Message = await conversation.get_response()
    assert (
        "Unfortunately, no tours are available for you at the moment"
        in response.message
    ), "Unexpected response to a user without tours"
