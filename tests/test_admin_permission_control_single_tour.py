from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from telethon.events import MessageEdited
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation
from telethon.tl.types.messages import BotCallbackAnswer

from tests.conftest import get_phone_number_request
from tour_guide_bot.models.admin import Admin
from tour_guide_bot.models.guide import Guest, Subscription


@pytest.mark.usefixtures("app", "tours")
async def test_approve_known_user(
    admin_conversation: Conversation,
    tours_as_dicts: list[dict],
    admin: Admin,
    guest: Guest,
    db_engine: AsyncEngine,
):
    await admin_conversation.send_message("/approve")
    response: Message = await admin_conversation.get_response()

    assert "Please select the tour." == response.message, (
        "Unexpected response to the /approve command"
    )

    response = await response.click(
        text=tours_as_dicts[0]["translations"]["en"]["title"]
    )
    assert isinstance(response, BotCallbackAnswer)

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    assert "Enter the phone number" in event.message.message

    await admin_conversation.send_message(admin.phone)
    response: Message = await admin_conversation.get_response()
    assert "How long the user should have access" in response.message, (
        "Unexpected grant duration request message"
    )

    now = datetime.now()
    await admin_conversation.send_message("7")
    response: Message = await admin_conversation.get_response()
    assert "was approved for the tour" in response.message, (
        "Unexpected grant confirmation"
    )

    await admin_conversation.send_message("/guest")
    response: Message = await admin_conversation.get_response()
    assert "in guest mode now" in response.message, (
        "Unexpected message in response to the guest mode switch"
    )

    await admin_conversation.send_message("/tours")

    response: Message = await admin_conversation.get_response()
    assert "Only one tour is available for you: Test tour" in response.message

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        stmt = select(Subscription).where(Subscription.guest == guest)
        s: Subscription | None = await session.scalar(stmt)

        assert (s.expire_ts - now).days == 7, "Unexpected subscription duration"


@pytest.mark.usefixtures("app", "tours")
async def test_approve_unknown_user(
    admin_conversation: Conversation,
    tours_as_dicts: list[dict],
    admin: Admin,
):
    await admin_conversation.send_message("/approve")
    response: Message = await admin_conversation.get_response()

    assert "Please select the tour." == response.message, (
        "Unexpected response to the /approve command"
    )

    response = await response.click(
        text=tours_as_dicts[0]["translations"]["en"]["title"]
    )
    assert isinstance(response, BotCallbackAnswer)

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    assert "Enter the phone number" in event.message.message

    await admin_conversation.send_message(admin.phone)
    response: Message = await admin_conversation.get_response()
    assert "How long the user should have access" in response.message, (
        "Unexpected grant duration request message"
    )

    await admin_conversation.send_message("1")
    response: Message = await admin_conversation.get_response()
    assert "was approved for the tour" in response.message, (
        "Unexpected grant confirmation"
    )

    await admin_conversation.send_message("/guest")
    response: Message = await admin_conversation.get_response()
    assert "in guest mode now" in response.message, (
        "Unexpected message in response to the guest mode switch"
    )

    await admin_conversation.send_message("/start")

    # skip welcome message
    await admin_conversation.get_response()

    response: Message = await get_phone_number_request(admin_conversation)
    await response.click(0, share_phone=True)

    response: Message = await admin_conversation.get_response()
    assert "I see you have a tour available" in response.message, (
        "Unexpected response to a user with a single tour"
    )


@pytest.mark.usefixtures("app", "guest", "tours", "approved_tours")
async def test_revoke(
    admin_conversation: Conversation,
    tours_as_dicts: list[dict],
    admin: Admin,
):
    await admin_conversation.send_message("/revoke")
    response: Message = await admin_conversation.get_response()

    assert "Please select the tour" in response.message

    response = await response.click(
        text=tours_as_dicts[0]["translations"]["en"]["title"]
    )
    assert isinstance(response, BotCallbackAnswer)

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    assert "Enter the phone number" in event.message.message

    await admin_conversation.send_message(admin.phone)
    response: Message = await admin_conversation.get_response()
    assert "Are you sure" in response.message

    response = await response.click(text="Yes")
    assert isinstance(response, BotCallbackAnswer)

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())

    assert "was revoked from" in event.message.message

    await admin_conversation.send_message("/guest")

    # skip mode switch confirmation
    await admin_conversation.get_response()

    await admin_conversation.send_message("/start")

    # skip welcome message
    await admin_conversation.get_response()

    response: Message = await admin_conversation.get_response()
    assert (
        "Unfortunately, no tours are available for you at the moment"
        in response.message
    ), "Unexpected response to a user without tours"
