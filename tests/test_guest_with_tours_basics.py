import pytest
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation
from telethon.tl.types import MessageMediaGeo
from telethon.tl.types.messages import BotCallbackAnswer

from tour_guide_bot.models.guide import MessageType


@pytest.mark.approved_tour_ids(1)
@pytest.mark.usefixtures("app", "guest", "approved_tours")
async def test_single_tour(conversation: Conversation, tours_as_dicts: list[dict]):
    await conversation.send_message("/start")
    response: Message = await conversation.get_response()
    assert response.message == "welcome (en)", (
        "Unexpected first message from a configured bot"
    )

    response: Message = await conversation.get_response()
    assert "I see you have a tour available" in response.message, (
        "Unexpected response to a user with a single tour"
    )

    await conversation.send_message("/tours")
    response: Message = await conversation.get_response()
    assert (
        "Only one tour is available for you: %s"
        % (tours_as_dicts[0]["translations"]["en"]["title"])
    ) in response.message, "Unexpected response to /tours"

    for content in tours_as_dicts[0]["translations"]["en"]["sections"][0]["content"]:
        response: Message = await conversation.get_response()

        match content["type"]:
            case MessageType.text:
                assert response.message == content["content"]["text"], (
                    "Unexpected response message text"
                )

            case MessageType.location:
                assert response.media is not None
                assert isinstance(response.media, MessageMediaGeo)
                assert round(response.media.geo.lat, 3) == round(
                    content["content"]["latitude"], 3
                )
                assert round(response.media.geo.long, 3) == round(
                    content["content"]["longitude"], 3
                )

            case _:
                assert False, "Unsupported message type"

    response: Message = await conversation.get_response()

    assert "Are you ready to continue?" == response.message, (
        "Unexpected message after the end of a section"
    )


@pytest.mark.approved_tour_ids(1, 2)
@pytest.mark.tours(
    {
        "translations": {
            "en": {
                "title": "Test tour 1",
                "description": "Test tour 1 description.",
                "sections": [
                    {
                        "title": "Test section 1.1",
                        "content": [
                            {
                                "type": MessageType.text,
                                "content": {"text": r"Test text 1\.1\.1"},
                            },
                        ],
                    },
                    {
                        "title": "Test section 1.2",
                        "content": [
                            {
                                "type": MessageType.text,
                                "content": {"text": r"Test text 1\.2\.1"},
                            },
                        ],
                    },
                ],
            }
        }
    },
    {
        "translations": {
            "en": {
                "title": "Test tour 2",
                "description": "Test tour 2 description.",
                "sections": [
                    {
                        "title": "Test section 2.1",
                        "content": [
                            {
                                "type": MessageType.text,
                                "content": {"text": r"Test text 2\.1\.1"},
                            },
                        ],
                    },
                    {
                        "title": "Test section 2.2",
                        "content": [
                            {
                                "type": MessageType.text,
                                "content": {"text": r"Test text 2\.2\.1"},
                            },
                        ],
                    },
                ],
            }
        }
    },
)
@pytest.mark.usefixtures("app", "guest", "approved_tours")
async def test_multiple_tours(conversation: Conversation, tours_as_dicts: list[dict]):
    await conversation.send_message("/start")
    response: Message = await conversation.get_response()
    assert response.message == "welcome (en)", (
        "Unexpected first message from a configured bot"
    )

    response: Message = await conversation.get_response()
    assert "I see you have 2 tours available" in response.message, (
        "Unexpected response to a user with a single tour"
    )

    await conversation.send_message("/tours")
    response: Message = await conversation.get_response()
    assert "Please select a tour you want to start." == response.message

    response = await response.click(
        text=tours_as_dicts[1]["translations"]["en"]["title"]
    )
    assert isinstance(response, BotCallbackAnswer)

    response: Message = await conversation.get_response()
    assert (
        "selected the tour %s" % tours_as_dicts[1]["translations"]["en"]["title"]
    ) in response.message, "Unexpected response to /tours"

    response: Message = await conversation.get_response()
    assert (
        tours_as_dicts[1]["translations"]["en"]["sections"][0]["content"][0]["content"][
            "text"
        ].replace(r"\.", ".")
        == response.message
    ), "Unexpected first section of the tour 2"

    response: Message = await conversation.get_response()
    assert "Are you ready to continue?" == response.message, (
        "Unexpected message after the end of a section"
    )


@pytest.mark.approved_tour_ids(2)
@pytest.mark.tours(
    {
        "translations": {
            "en": {
                "title": "Test tour 1",
                "description": "Test tour 1 description.",
                "sections": [
                    {
                        "title": "Test section 1.1",
                        "content": [
                            {
                                "type": MessageType.text,
                                "content": {"text": r"Test text 1\.1\.1"},
                            },
                        ],
                    },
                    {
                        "title": "Test section 1.2",
                        "content": [
                            {
                                "type": MessageType.text,
                                "content": {"text": r"Test text 1\.2\.1"},
                            },
                        ],
                    },
                ],
            }
        }
    },
    {
        "translations": {
            "en": {
                "title": "Test tour 2",
                "description": "Test tour 2 description.",
                "sections": [
                    {
                        "title": "Test section 2.1",
                        "content": [
                            {
                                "type": MessageType.text,
                                "content": {"text": r"Test text 2\.1\.1"},
                            },
                        ],
                    },
                    {
                        "title": "Test section 2.2",
                        "content": [
                            {
                                "type": MessageType.text,
                                "content": {"text": r"Test text 2\.2\.1"},
                            },
                        ],
                    },
                ],
            }
        }
    },
)
@pytest.mark.usefixtures("app", "guest", "approved_tours")
async def test_multiple_tours_one_approved(
    conversation: Conversation, tours_as_dicts: list[dict]
):
    await conversation.send_message("/start")
    response: Message = await conversation.get_response()
    assert response.message == "welcome (en)", (
        "Unexpected first message from a configured bot"
    )

    response: Message = await conversation.get_response()
    assert "I see you have a tour available" in response.message, (
        "Unexpected response to a user with a single tour"
    )

    await conversation.send_message("/tours")
    response: Message = await conversation.get_response()
    assert (
        "Only one tour is available for you: %s"
        % tours_as_dicts[1]["translations"]["en"]["title"]
    ) in response.message, "Unexpected response to /tours"

    response: Message = await conversation.get_response()
    assert (
        tours_as_dicts[1]["translations"]["en"]["sections"][0]["content"][0]["content"][
            "text"
        ].replace(r"\.", ".")
        == response.message
    ), "Unexpected first section of the tour 2"

    response: Message = await conversation.get_response()
    assert "Are you ready to continue?" == response.message, (
        "Unexpected message after the end of a section"
    )
