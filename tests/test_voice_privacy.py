from pathlib import Path

import pytest
from telethon import TelegramClient, utils
from telethon.errors import PremiumAccountRequiredError
from telethon.events import MessageEdited
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation
from telethon.tl.functions.account import SetPrivacyRequest
from telethon.tl.types import (
    InputPrivacyKeyVoiceMessages,
    InputPrivacyValueAllowAll,
    InputPrivacyValueAllowUsers,
    InputPrivacyValueDisallowAll,
)

from tour_guide_bot.bot.app import Application
from tour_guide_bot.models.guide import MessageType

MEDIA = Path(__file__).parent / "media"

# The "Voice messages" privacy setting; restricting it requires Premium
EVERYBODY = "everybody"
NOBODY = "nobody"
NOBODY_BUT_THE_BOT = "nobody but the bot"


@pytest.fixture
async def media_file_ids(app: Application, telegram_client: TelegramClient) -> dict:
    """Bot-side file_ids of the test media: the bot can only send files it knows."""
    me = await telegram_client.get_me()
    # Uploads can take a while, longer than the default timeouts
    timeouts = {"read_timeout": 60, "write_timeout": 60}
    voice = await app.bot.send_voice(me.id, MEDIA / "voice.ogg", **timeouts)
    video_note = await app.bot.send_video_note(
        me.id, MEDIA / "video_note.mp4", **timeouts
    )
    for message in (voice, video_note):
        await message.delete()

    return {
        MessageType.voice: voice.voice.file_id,
        MessageType.video_note: video_note.video_note.file_id,
    }


@pytest.fixture
def tours_as_dicts(media_file_ids: dict) -> list[dict]:
    return [
        {
            "translations": {
                "en": {
                    "title": "Test tour en",
                    "description": "Test tour description en.",
                    "sections": [
                        {
                            "title": "Test section 1 en",
                            "content": [
                                {
                                    "type": message_type,
                                    "content": {
                                        "files": [
                                            {"file_id": media_file_ids[message_type]}
                                        ]
                                    },
                                }
                                for message_type in (
                                    MessageType.voice,
                                    MessageType.video_note,
                                )
                            ]
                            + [
                                {
                                    "type": MessageType.text,
                                    "content": {"text": "After the media"},
                                }
                            ],
                        },
                        {
                            "title": "Test section 2 en",
                            "content": [
                                {
                                    "type": MessageType.text,
                                    "content": {"text": "Test text 2 en"},
                                }
                            ],
                        },
                    ],
                }
            },
        }
    ]


@pytest.fixture
async def voice_privacy(
    request: pytest.FixtureRequest,
    telegram_client: TelegramClient,
    bot_id: int,
    media_file_ids: dict,  # the bot must get the file_ids before it's blocked
):
    rules = {
        EVERYBODY: [InputPrivacyValueAllowAll()],
        NOBODY: [InputPrivacyValueDisallowAll()],
        NOBODY_BUT_THE_BOT: [
            InputPrivacyValueAllowUsers(
                [utils.get_input_user(await telegram_client.get_input_entity(bot_id))]
            ),
            InputPrivacyValueDisallowAll(),
        ],
    }[request.param]

    try:
        await telegram_client(SetPrivacyRequest(InputPrivacyKeyVoiceMessages(), rules))
    except PremiumAccountRequiredError:
        pytest.skip("Restricting voice messages needs a Premium test account")

    yield request.param

    await telegram_client(
        SetPrivacyRequest(InputPrivacyKeyVoiceMessages(), [InputPrivacyValueAllowAll()])
    )


async def start_tour(conversation: Conversation):
    await conversation.send_message("/start")
    response: Message = await conversation.get_response()
    assert response.message == "welcome (en)"
    response = await conversation.get_response()
    assert "I see you have a tour available" in response.message

    await conversation.send_message("/tours")
    response = await conversation.get_response()
    assert "Only one tour is available for you" in response.message


@pytest.mark.enabled_languages("en")
@pytest.mark.approved_tour_ids(1)
@pytest.mark.usefixtures("app", "guest", "approved_tours")
@pytest.mark.parametrize(
    "voice_privacy", [EVERYBODY, NOBODY_BUT_THE_BOT], indirect=True
)
async def test_guest_gets_voice_and_video_note(
    conversation: Conversation, voice_privacy: str
):
    await start_tour(conversation)

    response: Message = await conversation.get_response()
    assert response.voice is not None, "Expected a voice message"

    response = await conversation.get_response()
    assert response.video_note is not None, "Expected a video note"

    response = await conversation.get_response()
    assert response.message == "After the media"
    response = await conversation.get_response()
    assert response.message == "Are you ready to continue?"


@pytest.mark.enabled_languages("en")
@pytest.mark.approved_tour_ids(1)
@pytest.mark.usefixtures("app", "guest", "approved_tours")
@pytest.mark.parametrize("voice_privacy", [NOBODY], indirect=True)
async def test_guest_blocking_voice_messages_gets_files_and_explanation(
    conversation: Conversation, voice_privacy: str
):
    await start_tour(conversation)

    response: Message = await conversation.get_response(timeout=30)
    assert response.voice is None, "Expected a bare file instead of the voice"
    assert response.document is not None
    assert response.file.name == "voice.ogg"

    response = await conversation.get_response()
    assert "privacy settings block voice messages" in response.message

    response = await conversation.get_response(timeout=30)
    assert response.video_note is None, "Expected a bare file instead of the video note"
    assert response.document is not None
    assert response.file.name == "video.mp4"

    # The explanation isn't repeated within the section
    response = await conversation.get_response()
    assert response.message == "After the media", "The section send got stuck"
    response = await conversation.get_response()
    assert response.message == "Are you ready to continue?"


async def upload_audio_for_conversion(conversation: Conversation) -> Message:
    await conversation.send_message("/tours")
    response: Message = await conversation.get_response()
    assert await response.click(text="Add a tour") is not None

    event: MessageEdited.Event = await conversation.wait_event(MessageEdited())
    assert "send me the title" in event.message.message
    await conversation.send_message("Test tour")
    response = await conversation.get_response()
    assert "send me the description" in response.message
    await conversation.send_message("Test tour description")
    response = await conversation.get_response()
    assert "title for the new section" in response.message
    await conversation.send_message("Section 1")
    response = await conversation.get_response()
    assert "Now send me a" in response.message

    await conversation.send_file(MEDIA / "audio.mp3")
    response = await conversation.get_response()
    assert "convert this audio file to a voice message" in response.message
    assert await response.click(text="Yes") is not None

    return response


@pytest.mark.enabled_languages("en")
@pytest.mark.usefixtures("app", "guest")
@pytest.mark.parametrize(
    "voice_privacy", [EVERYBODY, NOBODY_BUT_THE_BOT], indirect=True
)
async def test_admin_gets_converted_voice_preview(
    admin_conversation: Conversation, voice_privacy: str
):
    conversation = admin_conversation
    await upload_audio_for_conversion(conversation)

    response: Message = await conversation.get_response(timeout=30)
    assert response.voice is not None, "Expected the converted voice preview"
    assert await response.click(text="Store the voice message") is not None

    response = await conversation.get_response()
    assert "The voice was added to the section!" in response.message


@pytest.mark.enabled_languages("en")
@pytest.mark.usefixtures("app", "guest")
@pytest.mark.parametrize("voice_privacy", [NOBODY], indirect=True)
async def test_admin_blocking_voice_messages_is_told_why(
    admin_conversation: Conversation, voice_privacy: str
):
    conversation = admin_conversation
    message = await upload_audio_for_conversion(conversation)

    while True:
        event: MessageEdited.Event = await conversation.wait_event(
            MessageEdited(func=lambda e: e.message.id == message.id), timeout=30
        )
        if "privacy settings block voice messages" in event.message.message:
            break
        assert "Something went wrong" not in event.message.message

    assert await event.message.click(text="Store the original audio") is not None
    response: Message = await conversation.get_response()
    assert "The audio was added to the section!" in response.message
