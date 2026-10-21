from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.error import BadRequest

from tour_guide_bot.bot.guide.tours import ToursCommandHandler
from tour_guide_bot.models.guide import MessageType


# The fallbacks for blocked voice messages are covered in test_voice_privacy.py
@pytest.mark.parametrize(
    "message_type, blocked_send",
    [
        (MessageType.voice, "send_voice"),
        (MessageType.video_note, "send_video_note"),
    ],
)
async def test_other_errors_are_not_swallowed(
    message_type: MessageType, blocked_send: str
):
    bot = AsyncMock()
    getattr(bot, blocked_send).side_effect = BadRequest("Chat not found")
    context = MagicMock()
    context.bot = bot

    # send_section runs after the handler's db session is gone, so it gets none
    handler = ToursCommandHandler(db_session=None)
    with pytest.raises(BadRequest):
        await handler.send_section(
            None,
            context,
            chat_id=42,
            contents=[(message_type, {"files": [{"file_id": "original-file-id"}]})],
            delay="0",
            protect_content=True,
            language="en",
            translation_id=1,
            position=0,
            is_last_section=True,
        )

    bot.send_document.assert_not_awaited()
    bot.send_message.assert_not_awaited()
