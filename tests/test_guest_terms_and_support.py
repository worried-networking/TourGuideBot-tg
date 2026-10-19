import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation

from tour_guide_bot.models.settings import Settings, SettingsKey


@pytest.mark.usefixtures("unconfigured_app", "guest")
async def test_no_support_message(conversation: Conversation):
    await conversation.send_message("/support")
    response: Message = await conversation.get_response()
    assert "There are no support details yet" in response.message, (
        "Unexpected response from an unconfigured bot"
    )


@pytest.mark.usefixtures("unconfigured_app", "guest")
async def test_no_terms_message(conversation: Conversation):
    await conversation.send_message("/terms")
    response: Message = await conversation.get_response()
    assert "There are no terms & conditions yet" in response.message, (
        "Unexpected response from an unconfigured bot"
    )


@pytest.mark.usefixtures("app", "guest")
async def test_has_support_message(conversation: Conversation):
    await conversation.send_message("/support")
    response: Message = await conversation.get_response()
    assert response.message == "support (en)", (
        "Unexpected response from a configured bot"
    )


@pytest.mark.usefixtures("app", "guest")
async def test_has_terms_message(conversation: Conversation):
    await conversation.send_message("/terms")
    response: Message = await conversation.get_response()
    assert response.message == "terms (en)", "Unexpected response from a configured bot"


@pytest.mark.enabled_languages("en", "ru")
@pytest.mark.usefixtures("app", "guest")
async def test_has_terms_message_multilang(
    conversation: Conversation, db_engine: AsyncEngine
):
    await conversation.send_message("/terms")
    response: Message = await conversation.get_response()
    assert response.message == "terms (en)", "Unexpected response from a configured bot"

    await conversation.send_message("/language")
    msg = await conversation.get_response()
    await msg.click(text="Russian (Русский)")

    await conversation.send_message("/terms")
    response: Message = await conversation.get_response()
    assert response.message == "terms (ru)", "Unexpected response from a configured bot"

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        terms = await Settings.load(session, SettingsKey.terms_message, "ru")
        await session.delete(terms)
        await session.commit()

    await conversation.send_message("/terms")
    response: Message = await conversation.get_response()
    assert "Условия использования пока не опубликованы" in response.message, (
        "Unexpected response from a configured bot"
    )

    await conversation.send_message("/language")
    msg = await conversation.get_response()
    await msg.click(text="Английский (English)")

    await conversation.send_message("/terms")
    response: Message = await conversation.get_response()
    assert response.message == "terms (en)", "Unexpected response from a configured bot"


@pytest.mark.enabled_languages("en", "ru")
@pytest.mark.usefixtures("app", "guest")
async def test_has_support_message_multilang(
    conversation: Conversation, db_engine: AsyncEngine
):
    await conversation.send_message("/support")
    response: Message = await conversation.get_response()
    assert response.message == "support (en)", (
        "Unexpected response from a configured bot"
    )

    await conversation.send_message("/language")
    msg = await conversation.get_response()
    await msg.click(text="Russian (Русский)")

    await conversation.send_message("/support")
    response: Message = await conversation.get_response()
    assert response.message == "support (ru)", (
        "Unexpected response from a configured bot"
    )

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        support = await Settings.load(session, SettingsKey.support_message, "ru")
        await session.delete(support)
        await session.commit()

    await conversation.send_message("/support")
    response: Message = await conversation.get_response()
    assert "Сведения о поддержке пока отсутствуют" in response.message, (
        "Unexpected response from a configured bot"
    )

    await conversation.send_message("/language")
    msg = await conversation.get_response()
    await msg.click(text="Английский (English)")

    await conversation.send_message("/support")
    response: Message = await conversation.get_response()
    assert response.message == "support (en)", (
        "Unexpected response from a configured bot"
    )
