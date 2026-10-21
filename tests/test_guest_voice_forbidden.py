from unittest.mock import AsyncMock

import pytest
from telegram.error import BadRequest

from tour_guide_bot.bot.guide.tours import SectionDelivery, ToursCommandHandler
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

    # send_section skips a failed part, the fallback mustn't hide the failure
    with pytest.raises(BadRequest):
        await ToursCommandHandler.send_part(
            bot,
            SectionDelivery(
                chat_id=42,
                user_id=42,
                run_id="run",
                translation_id=1,
                position=0,
                is_last_section=True,
                language="en",
                protect_content=True,
                delay="0",
                contents=[],
            ),
            message_type,
            {"files": [{"file_id": "original-file-id"}]},
            voice_messages_blocked=False,
        )

    bot.send_document.assert_not_awaited()
    bot.send_message.assert_not_awaited()
