import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation

from tour_guide_bot.models.settings import Settings, SettingsKey


async def _receive_tour_content(
    conversation: Conversation, tours_as_dicts: list[dict]
) -> list[Message]:
    await conversation.send_message("/start")
    response: Message = await conversation.get_response()
    assert response.message == "welcome (en)", (
        "Unexpected first message from a configured bot"
    )

    response = await conversation.get_response()
    assert "I see you have a tour available" in response.message, (
        "Unexpected response to a user with a single tour"
    )

    await conversation.send_message("/tours")
    response = await conversation.get_response()
    assert "Only one tour is available for you" in response.message, (
        "Unexpected response to /tours"
    )

    section = tours_as_dicts[0]["translations"]["en"]["sections"][0]
    content_messages = [await conversation.get_response() for _ in section["content"]]

    response = await conversation.get_response()
    assert "Are you ready to continue?" == response.message, (
        "Unexpected message after the end of a section"
    )

    return content_messages


@pytest.mark.approved_tour_ids(1)
@pytest.mark.usefixtures("app", "guest", "approved_tours")
async def test_tour_content_protected_by_default(
    conversation: Conversation, tours_as_dicts: list[dict]
):
    content_messages = await _receive_tour_content(conversation, tours_as_dicts)

    for msg in content_messages:
        assert msg.noforwards, (
            "Tour content must be protected when protect_content isn't set"
        )


@pytest.mark.approved_tour_ids(1)
@pytest.mark.usefixtures("app", "guest", "approved_tours")
async def test_tour_content_not_protected_when_disabled(
    conversation: Conversation, db_engine: AsyncEngine, tours_as_dicts: list[dict]
):
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        session.add(Settings(key=SettingsKey.protect_content, value="no"))
        await session.commit()

    content_messages = await _receive_tour_content(conversation, tours_as_dicts)

    for msg in content_messages:
        assert not msg.noforwards, (
            "Tour content must not be protected when protect_content is disabled"
        )
