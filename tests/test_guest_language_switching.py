import pytest
from telethon.events import MessageEdited
from telethon.tl.custom import Message
from telethon.tl.custom.conversation import Conversation
from telethon.tl.types.messages import BotCallbackAnswer


@pytest.mark.usefixtures("app", "guest")
@pytest.mark.enabled_languages("en")
async def test_single_language(conversation: Conversation):
    await conversation.send_message("/language")
    response: Message = await conversation.get_response()
    assert (
        "you can`t change the language — this bot supports only one" in response.message
    ), (
        "Unexpected response to the language switch from a bot that support only one language"
    )


@pytest.mark.usefixtures("app", "guest")
@pytest.mark.enabled_languages("en", "ru")
async def test_multiple_languages(conversation: Conversation):
    await conversation.send_message("/language")
    response: Message = await conversation.get_response()
    assert "Please select the language you prefer" in response.message, (
        "Unexpected language selection message"
    )

    response = await response.click(text="Russian (Русский)")
    assert isinstance(response, BotCallbackAnswer), (
        "BotCallbackAnswer didn't arrive after the inline button click"
    )
    await conversation.wait_event(MessageEdited())

    await conversation.send_message("/language")
    response: Message = await conversation.get_response()
    assert "Пожалуйста, выберите предпочитаемый язык" in response.message, (
        "Unexpected language selection message in the second language"
    )
