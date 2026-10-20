from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import InputFile
from telegram.error import BadRequest

from tour_guide_bot.bot.guide.tours import ToursCommandHandler
from tour_guide_bot.models.guide import MessageType


async def send_voice_section(bot):
    context = MagicMock()
    context.bot = bot
    # send_section doesn't touch self when sending the last section
    await ToursCommandHandler.send_section(
        None,
        None,
        context,
        chat_id=42,
        contents=[
            (
                MessageType.voice,
                {"files": [{"file_id": "voice-file-id", "caption": "Hi"}]},
            )
        ],
        delay="0",
        protect_content=True,
        language="en",
        translation_id=1,
        position=0,
        is_last_section=True,
    )


async def test_voice_is_reuploaded_as_audio_when_voice_messages_are_forbidden():
    bot = AsyncMock()
    bot.send_voice.side_effect = BadRequest("Voice_messages_forbidden")
    voice = AsyncMock()
    voice.download_as_bytearray.return_value = bytearray(b"ogg data")
    bot.get_file.return_value = voice

    await send_voice_section(bot)

    bot.get_file.assert_awaited_once_with("voice-file-id")
    bot.send_audio.assert_awaited_once()
    args, kwargs = bot.send_audio.call_args
    assert args[0] == 42
    assert isinstance(args[1], InputFile)
    assert args[1].input_file_content == b"ogg data"
    assert kwargs["caption"] == "Hi"
    assert kwargs["protect_content"] is True


async def test_other_voice_errors_are_not_swallowed():
    bot = AsyncMock()
    bot.send_voice.side_effect = BadRequest("Chat not found")

    with pytest.raises(BadRequest):
        await send_voice_section(bot)

    bot.send_audio.assert_not_awaited()
