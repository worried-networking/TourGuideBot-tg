import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from telegram import Message as TelegramMessage
from telethon.events import MessageEdited
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation

from tour_guide_bot.models.settings import PaymentProvider

# Long enough for the next message to reach the bot while the handler that
# sent the reply is still running, short enough for the 10s conversation timeout.
SLOW = 2


@pytest.mark.skip_payment_token_stub
@pytest.mark.usefixtures("app", "admin")
async def test_message_right_after_reply_is_handled_in_new_state(
    admin_conversation: Conversation, db_engine: AsyncEngine, mocker
):
    """The next message must not be routed by the state the bot is leaving."""
    original = TelegramMessage.reply_text

    async def slow_reply_text(*args, **kwargs):
        ret = await original(*args, **kwargs)
        await asyncio.sleep(SLOW)
        return ret

    mocker.patch.object(TelegramMessage, "reply_text", new=slow_reply_text)

    await admin_conversation.send_message("/configure")
    response: Message = await admin_conversation.get_response()
    assert await response.click(text="Payments") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    assert await event.message.click(text="Add payment token") is not None

    event = await admin_conversation.wait_event(MessageEdited())
    assert "send me the name of" in event.message.message

    await admin_conversation.send_message("provider name")
    response = await admin_conversation.get_response()
    assert "send me the payment token" in response.message

    await admin_conversation.send_message("payment token")
    response = await admin_conversation.get_response()
    assert "provider has been added" in response.message, (
        "The token was handled by the previous conversation state"
    )

    async with AsyncSession(db_engine) as session:
        provider = await session.scalar(select(PaymentProvider))
        assert provider.name == "provider name"
        assert provider.config["token"] == "payment token"
