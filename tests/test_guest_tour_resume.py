import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from telethon.events import MessageEdited
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation
from telethon.tl.types import MessageMediaGeo
from telethon.tl.types.messages import BotCallbackAnswer

from tour_guide_bot.models.guide import MessageType
from tour_guide_bot.models.settings import Settings, SettingsKey


async def start_tour(conversation: Conversation) -> None:
    await conversation.send_message("/start")
    response: Message = await conversation.get_response()
    assert response.message == "welcome (en)"
    response = await conversation.get_response()
    assert "I see you have a tour available" in response.message

    await conversation.send_message("/tours")
    response = await conversation.get_response()
    assert "Only one tour is available for you" in response.message


async def assert_no_more_messages(conversation: Conversation, timeout: int = 10):
    with pytest.raises(asyncio.TimeoutError):
        response = await conversation.get_response(timeout=timeout)
        pytest.fail(f"Unexpected message: {response.message!r}")


@pytest.mark.approved_tour_ids(1)
@pytest.mark.usefixtures("app", "guest", "approved_tours")
async def test_restart_mid_section_resumes_it(
    conversation: Conversation, restart_app, db_engine: AsyncEngine
):
    # The restart takes about a second; a part sent while the bot stops can
    # come twice, so leave it a wide margin
    async with AsyncSession(db_engine) as session:
        session.add(
            Settings(key=SettingsKey.delay_between_messages, language=None, value="8")
        )
        await session.commit()

    await start_tour(conversation)

    response: Message = await conversation.get_response()
    assert response.message == "Test text 1 en", "Unexpected first section content"

    # The rest of the section comes with the delay between messages, so the
    # restart lands in the middle of it
    await restart_app()

    response = await conversation.get_response(timeout=30)
    assert isinstance(response.media, MessageMediaGeo), (
        "The section wasn't resumed after the restart"
    )
    response = await conversation.get_response(timeout=20)
    assert response.message == "Test text 2 en"
    response = await conversation.get_response(timeout=20)
    assert response.message == "Are you ready to continue?"

    await assert_no_more_messages(conversation)

    answer = await response.click(text="Next section")
    assert isinstance(answer, BotCallbackAnswer)
    response = await conversation.get_response()
    assert response.message == "Test text 3 en", (
        "The prompt sent after the restart doesn't lead to the next section"
    )


@pytest.mark.approved_tour_ids(1)
@pytest.mark.tours(
    {
        "translations": {
            "en": {
                "title": "Test tour 1",
                "description": "Test tour 1 description.",
                "sections": [
                    {
                        "title": "Test section 1",
                        "content": [
                            {
                                "type": MessageType.text,
                                "content": {"text": "Before"},
                            },
                            {
                                # An unescaped dot is invalid MarkdownV2
                                "type": MessageType.text,
                                "content": {"text": "Broken."},
                            },
                            {
                                "type": MessageType.text,
                                "content": {"text": "After"},
                            },
                        ],
                    },
                    {
                        "title": "Test section 2",
                        "content": [
                            {
                                "type": MessageType.text,
                                "content": {"text": "Next"},
                            },
                        ],
                    },
                ],
            }
        },
    }
)
@pytest.mark.usefixtures("app", "guest", "approved_tours")
async def test_failed_part_doesnt_stop_section(conversation: Conversation):
    await start_tour(conversation)

    response: Message = await conversation.get_response()
    assert response.message == "Before"
    response = await conversation.get_response(timeout=15)
    assert response.message == "After", "The section stopped at the broken part"
    response = await conversation.get_response()
    assert response.message == "Are you ready to continue?"

    assert await response.click(text="Abort") is not None
    event: MessageEdited.Event = await conversation.wait_event(MessageEdited())
    assert event.message.message == "Cancelled."
