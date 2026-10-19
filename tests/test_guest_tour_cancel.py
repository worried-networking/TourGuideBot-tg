import asyncio

import pytest
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation


@pytest.mark.approved_tour_ids(1)
@pytest.mark.usefixtures("app", "guest", "approved_tours")
async def test_cancel_stops_section_being_sent(conversation: Conversation):
    await conversation.send_message("/start")
    response: Message = await conversation.get_response()
    assert response.message == "welcome (en)"
    response = await conversation.get_response()
    assert "I see you have a tour available" in response.message

    await conversation.send_message("/tours")
    response = await conversation.get_response()
    assert "Only one tour is available for you" in response.message

    response = await conversation.get_response()
    assert response.message == "Test text 1 en", "Unexpected first section content"

    # The rest of the section comes with the default 4s delay between messages,
    # so without the cancellation the location would arrive first
    await conversation.send_message("/cancel")
    response = await conversation.get_response(timeout=6)
    assert response.message == "Cancelled.", "/cancel wasn't handled during the send"

    with pytest.raises(asyncio.TimeoutError):
        response = await conversation.get_response(timeout=10)
        pytest.fail(f"Unexpected message after /cancel: {response.message!r}")


@pytest.mark.approved_tour_ids(1)
@pytest.mark.usefixtures("app", "guest", "approved_tours")
async def test_tours_restarts_tour_in_progress(conversation: Conversation):
    """A section whose send died leaves no buttons; /tours must still get out of it."""
    await conversation.send_message("/start")
    response: Message = await conversation.get_response()
    assert response.message == "welcome (en)"
    response = await conversation.get_response()
    assert "I see you have a tour available" in response.message

    await conversation.send_message("/tours")
    response = await conversation.get_response()
    assert "Only one tour is available for you" in response.message
    response = await conversation.get_response()
    assert response.message == "Test text 1 en", "Unexpected first section content"

    await conversation.send_message("/tours")
    response = await conversation.get_response(timeout=6)
    assert "Only one tour is available for you" in response.message, (
        "/tours wasn't handled during the tour"
    )
    response = await conversation.get_response()
    assert response.message == "Test text 1 en", "The previous send wasn't stopped"
