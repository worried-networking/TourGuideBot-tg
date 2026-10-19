import pytest
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation


@pytest.mark.usefixtures("app", "guest", "admin")
async def test_switching_mode_multiple_times(conversation: Conversation):
    await conversation.send_message("/admin")
    response: Message = await conversation.get_response()

    assert "Welcome to the admin mode" in response.message, (
        "Unexpected message in response to the admin mode switch"
    )

    await conversation.send_message("/guest")
    response: Message = await conversation.get_response()

    assert "in guest mode now" in response.message, (
        "Unexpected message in response to the guest mode switch"
    )

    await conversation.send_message("/admin")
    response: Message = await conversation.get_response()

    assert "Welcome to the admin mode" in response.message, (
        "Unexpected message in response to the admin mode switch"
    )

    await conversation.send_message("/guest")
    response: Message = await conversation.get_response()

    assert "in guest mode now" in response.message, (
        "Unexpected message in response to the guest mode switch"
    )
