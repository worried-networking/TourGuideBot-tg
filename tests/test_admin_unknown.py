import hashlib
from asyncio import sleep

import pytest
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation

from .conftest import get_phone_number_request


@pytest.mark.usefixtures("app")
async def test_success_auth_flow_configured_app(
    conversation: Conversation, bot_token: str
):
    await conversation.send_message("/admin")
    response: Message = await get_phone_number_request(conversation)
    await response.click(0, share_phone=True)
    await sleep(1)

    response: Message = await conversation.get_response()
    assert (
        "Please send me the md5 hash of the token to confirm ownership"
        in response.message
    ), "Unexpected response to an unknown phone number"

    await conversation.send_message(hashlib.md5(bot_token.encode()).hexdigest())

    response: Message = await conversation.get_response()

    assert "Admin permissions confirmed" in response.message, (
        "Unexpected message in response to the secret phrase"
    )


@pytest.mark.usefixtures("unconfigured_app")
async def test_success_auth_flow_unconfigured_app(
    conversation: Conversation, bot_token: str
):
    await conversation.send_message("/admin")
    response: Message = await get_phone_number_request(conversation)
    await response.click(0, share_phone=True)
    await sleep(1)

    response: Message = await conversation.get_response()
    assert (
        "Please send me the md5 hash of the token to confirm ownership"
        in response.message
    ), "Unexpected response to an unknown phone number"

    await conversation.send_message(hashlib.md5(bot_token.encode()).hexdigest())

    response: Message = await conversation.get_response()

    assert "Admin permissions confirmed" in response.message, (
        "Unexpected message in response to the secret phrase"
    )


@pytest.mark.usefixtures("app")
async def test_accepts_only_current_contact(conversation: Conversation):
    await conversation.send_message("/admin")
    response: Message = await get_phone_number_request(conversation)

    await response.click(0, share_phone="+99999999999")

    response: Message = await conversation.get_response()
    assert (
        "Please send me your contact number and not somebody else's" in response.message
    ), "Unexpected response to sending a random contact"


@pytest.mark.usefixtures("app")
async def test_incorrect_token(conversation: Conversation):
    await conversation.send_message("/admin")
    response: Message = await get_phone_number_request(conversation)
    await response.click(0, share_phone=True)
    await sleep(1)

    response: Message = await conversation.get_response()
    assert (
        "Please send me the md5 hash of the token to confirm ownership"
        in response.message
    ), "Unexpected response to an unknown phone number"

    await conversation.send_message("foo")

    response: Message = await conversation.get_response()

    assert "I still don't recognise you, sorry." in response.message, (
        "Unexpected message in response to the secret phrase"
    )
