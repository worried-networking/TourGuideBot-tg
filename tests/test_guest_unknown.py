import pytest
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation

from .conftest import get_phone_number_request


@pytest.mark.usefixtures("app")
async def test_success_auth_flow(conversation: Conversation):
    await conversation.send_message("/start")
    response: Message = await conversation.get_response()
    assert response.message == "welcome (en)", (
        "Unexpected first message from a configured bot"
    )

    response: Message = await get_phone_number_request(conversation)
    await response.click(0, share_phone=True)

    response: Message = await conversation.get_response()
    assert (
        "Unfortunately, no tours are available for you at the moment"
        in response.message
    ), "Unexpected response to a user without tours"


@pytest.mark.usefixtures("app")
async def test_accepts_only_current_contact(conversation: Conversation):
    await conversation.send_message("/start")
    response: Message = await conversation.get_response()
    assert response.message == "welcome (en)", (
        "Unexpected first message from a configured bot"
    )

    response: Message = await get_phone_number_request(conversation)
    await response.click(0, share_phone="+99999999999")

    response: Message = await conversation.get_response()
    assert (
        "Please send me your contact number and not somebody else's" in response.message
    ), "Unexpected response to sending a random contact"


@pytest.mark.usefixtures("app")
async def test_incorrect_commands_during_auth(conversation: Conversation):
    await conversation.send_message("/start")
    response: Message = await conversation.get_response()
    assert response.message == "welcome (en)", (
        "Unexpected first message from a configured bot"
    )

    await get_phone_number_request(conversation)

    await conversation.send_message("test")
    response: Message = await conversation.get_response()
    assert "Please send me your phone" in response.message, (
        "Unexpected response to an unexpected message during auth"
    )

    await conversation.send_message("/test")
    response: Message = await conversation.get_response()
    assert "Unknown command" in response.message, (
        "Unexpected response to an unexpected command during auth"
    )
