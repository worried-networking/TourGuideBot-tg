from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import InputFile
from telegram.error import BadRequest

from tour_guide_bot.bot.guide.tours import ToursCommandHandler
from tour_guide_bot.models.guide import MessageType


async def send_single_file_section(bot, message_type: MessageType):
    context = MagicMock()
    context.bot = bot
    # send_section runs after the handler's db session is gone, so it gets none
    handler = ToursCommandHandler(db_session=None)
    await handler.send_section(
        None,
        context,
        chat_id=42,
        contents=[
            (
                message_type,
                {"files": [{"file_id": "original-file-id", "caption": "Hi"}]},
            )
        ],
        delay="0",
        protect_content=True,
        language="en",
        translation_id=1,
        position=0,
        is_last_section=True,
    )


# Telegram's "Voice messages" privacy setting blocks video notes too
@pytest.mark.parametrize(
    "message_type, blocked_send, fallback_send",
    [
        (MessageType.voice, "send_voice", "send_audio"),
        (MessageType.video_note, "send_video_note", "send_video"),
    ],
)
async def test_file_is_reuploaded_when_voice_messages_are_forbidden(
    message_type: MessageType, blocked_send: str, fallback_send: str
):
    bot = AsyncMock()
    getattr(bot, blocked_send).side_effect = BadRequest("Voice_messages_forbidden")
    file = AsyncMock()
    file.download_as_bytearray.return_value = bytearray(b"file data")
    bot.get_file.return_value = file

    await send_single_file_section(bot, message_type)

    bot.get_file.assert_awaited_once_with("original-file-id")
    fallback = getattr(bot, fallback_send)
    fallback.assert_awaited_once()
    args, kwargs = fallback.call_args
    assert args[0] == 42
    assert isinstance(args[1], InputFile)
    assert args[1].input_file_content == b"file data"
    assert kwargs["caption"] == "Hi"
    assert kwargs["protect_content"] is True


@pytest.mark.parametrize(
    "message_type, blocked_send, fallback_send",
    [
        (MessageType.voice, "send_voice", "send_audio"),
        (MessageType.video_note, "send_video_note", "send_video"),
    ],
)
async def test_other_errors_are_not_swallowed(
    message_type: MessageType, blocked_send: str, fallback_send: str
):
    bot = AsyncMock()
    getattr(bot, blocked_send).side_effect = BadRequest("Chat not found")

    with pytest.raises(BadRequest):
        await send_single_file_section(bot, message_type)

    getattr(bot, fallback_send).assert_not_awaited()
