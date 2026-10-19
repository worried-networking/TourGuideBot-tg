import pytest
from sqlalchemy import Sequence, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from telethon.events import MessageEdited
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation

from tour_guide_bot.models.settings import PaymentProvider


@pytest.mark.usefixtures("app", "admin")
async def test_menu_available_when_have_support_and_terms(
    admin_conversation: Conversation,
):
    await admin_conversation.send_message("/configure")
    response: Message = await admin_conversation.get_response()
    assert await response.click(text="Payments") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "select the payment-related parameter" in msg.message, (
        "Unexpected message in response to the admin mode switch"
    )

    assert msg.button_count > 1

    assert await msg.click(msg.button_count - 1) is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "select the parameter you want to change" in msg.message


@pytest.mark.usefixtures("unconfigured_app", "admin")
async def test_menu_not_available_when_no_support_or_terms(
    admin_conversation: Conversation,
):
    await admin_conversation.send_message("/configure")
    response: Message = await admin_conversation.get_response()
    assert await response.click(text="Payments") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "You need to set up" in msg.message, (
        "Unexpected message in response to the admin mode switch"
    )

    assert msg.button_count == 1

    assert await msg.click(0) is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "select the parameter you want to change" in msg.message


@pytest.mark.usefixtures("app", "admin")
async def test_delete_payment_token_single(
    admin_conversation: Conversation, db_engine: AsyncEngine
):
    await admin_conversation.send_message("/configure")
    response: Message = await admin_conversation.get_response()
    assert await response.click(text="Payments") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert await msg.click(text="Delete payment token") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert await msg.click(text="Yes") is not None
    await admin_conversation.wait_event(MessageEdited())

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        stmt = select(PaymentProvider)
        providers: Sequence[PaymentProvider] = (await session.scalars(stmt)).all()

        assert len(providers) == 1

        assert not providers[0].enabled


@pytest.mark.payment_tokens_count(2)
@pytest.mark.usefixtures("app", "admin")
async def test_delete_payment_token_multiple(
    admin_conversation: Conversation, db_engine: AsyncEngine
):
    await admin_conversation.send_message("/configure")
    response: Message = await admin_conversation.get_response()
    assert await response.click(text="Payments") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert await msg.click(text="Delete payment token") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "Please select the payment provider" in msg.message
    assert await msg.click(text="test provider 1") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert await msg.click(text="Yes") is not None
    await admin_conversation.wait_event(MessageEdited())

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        stmt = select(PaymentProvider).order_by(PaymentProvider.id)
        providers: Sequence[PaymentProvider] = (await session.scalars(stmt)).all()

        assert len(providers) == 2

        assert not providers[0].enabled
        assert providers[1].enabled


@pytest.mark.usefixtures("app", "admin")
async def test_update_payment_token_single(
    admin_conversation: Conversation, db_engine: AsyncEngine
):
    await admin_conversation.send_message("/configure")
    response: Message = await admin_conversation.get_response()
    assert await response.click(text="Payments") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert await msg.click(text="Change payment token") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "send me the new payment token" in msg.message

    new_token = "new_payment_token"

    await admin_conversation.send_message(new_token)

    msg = await admin_conversation.get_response()

    assert "token has been updated" in msg.message

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        stmt = select(PaymentProvider)
        providers: Sequence[PaymentProvider] = (await session.scalars(stmt)).all()

        assert len(providers) == 1

        assert providers[0] is not None
        assert providers[0].enabled
        assert providers[0].config["token"] == new_token


@pytest.mark.payment_tokens_count(2)
@pytest.mark.usefixtures("app", "admin")
async def test_update_payment_token_multiple(
    admin_conversation: Conversation, db_engine: AsyncEngine
):
    await admin_conversation.send_message("/configure")
    response: Message = await admin_conversation.get_response()
    assert await response.click(text="Payments") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert await msg.click(text="Change payment token") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "Please select the payment provider" in msg.message
    assert await msg.click(text="test provider 1") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "send me the new payment token" in msg.message

    new_token = "new_payment_token"

    await admin_conversation.send_message("{} {}".format(new_token, 1))

    msg = await admin_conversation.get_response()

    assert "token has been updated" in msg.message

    await admin_conversation.send_message("/configure")
    response: Message = await admin_conversation.get_response()
    assert await response.click(text="Payments") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert await msg.click(text="Change payment token") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "Please select the payment provider" in msg.message
    assert await msg.click(text="test provider 2") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "send me the new payment token" in msg.message

    await admin_conversation.send_message("{} {}".format(new_token, 2))

    msg = await admin_conversation.get_response()

    assert "token has been updated" in msg.message

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        stmt = select(PaymentProvider)
        providers: Sequence[PaymentProvider] = (await session.scalars(stmt)).all()

        assert len(providers) == 2

        for provider in providers:
            assert provider is not None
            assert provider.enabled
            assert provider.name == "test provider {}".format(provider.id)
            assert provider.config["token"] == "{} {}".format(new_token, provider.id)


@pytest.mark.skip_payment_token_stub
@pytest.mark.usefixtures("app", "admin")
async def test_add_payment_token(
    admin_conversation: Conversation, db_engine: AsyncEngine
):
    await admin_conversation.send_message("/configure")
    response: Message = await admin_conversation.get_response()
    assert await response.click(text="Payments") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert await msg.click(text="Add payment token") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "send me the name of" in msg.message

    name = "provider name"
    token = "payment_token"

    await admin_conversation.send_message("{}-{}".format(name, 1))
    msg = await admin_conversation.get_response()

    assert "send me the payment token" in msg.message

    await admin_conversation.send_message("{}-{}".format(token, 1))
    msg = await admin_conversation.get_response()

    assert "provider has been added" in msg.message

    await admin_conversation.send_message("/configure")
    response: Message = await admin_conversation.get_response()
    assert await response.click(text="Payments") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert await msg.click(text="Add payment token") is not None

    event: MessageEdited.Event = await admin_conversation.wait_event(MessageEdited())
    msg: Message = event.message

    assert "send me the name of" in msg.message

    name = "provider name"
    token = "payment_token"

    await admin_conversation.send_message("{}-{}".format(name, 2))
    msg = await admin_conversation.get_response()

    assert "send me the payment token" in msg.message

    await admin_conversation.send_message("{}-{}".format(token, 2))
    msg = await admin_conversation.get_response()

    assert "provider has been added" in msg.message

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        stmt = select(PaymentProvider)
        providers: Sequence[PaymentProvider] = (await session.scalars(stmt)).all()

        assert len(providers) == 2

        for provider in providers:
            assert provider is not None
            assert provider.enabled
            assert provider.name == "{}-{}".format(name, provider.id)
            assert provider.config["token"] == "{}-{}".format(token, provider.id)
