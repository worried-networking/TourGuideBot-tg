"""Resuming interrupted sections, without the Bot API: the bot is a stub."""

import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from telegram.error import BadRequest, Forbidden, RetryAfter

from tour_guide_bot.bot.guide.tours import ToursCommandHandler
from tour_guide_bot.models.guide import (
    Guest,
    MessageType,
    Subscription,
    Tour,
    TourDelivery,
    TourSection,
    TourSectionContent,
    TourTranslation,
)
from tour_guide_bot.models.settings import Settings, SettingsKey
from tour_guide_bot.models.telegram import TelegramUser

USER_ID = 100
PROMPT = "Are you ready to continue?"


class StubBot:
    def __init__(self):
        self.sent: list[str] = []
        # Text -> errors to raise, one per attempt to send it
        self.errors: dict[str, list[Exception]] = {}

    async def send_chat_action(self, **kwargs):
        pass

    async def send_message(self, chat_id: int, text: str, *args, **kwargs):
        if self.errors.get(text):
            raise self.errors[text].pop(0)
        self.sent.append(text)


class StubApplication:
    running = True
    default_language = "en"

    def __init__(self, db_engine: AsyncEngine):
        self.db_engine = db_engine
        self.bot = StubBot()
        self.tasks: list[asyncio.Task] = []

    def create_task(self, coroutine, update=None) -> asyncio.Task:
        task = asyncio.create_task(coroutine)
        self.tasks.append(task)
        return task

    async def resume(self) -> list[str]:
        await ToursCommandHandler.resume_deliveries(self)
        await asyncio.gather(*self.tasks)
        return self.bot.sent


@pytest.fixture
async def translation_id(db_engine: AsyncEngine) -> int:
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        session.add(
            Settings(key=SettingsKey.delay_between_messages, language=None, value="0")
        )

        guest = Guest(phone="1")
        session.add(TelegramUser(id=USER_ID, guest=guest, language="en"))

        tour = Tour()
        translation = TourTranslation(tour=tour, language="en", title="Tour")
        for position, texts in enumerate([["A", "B", "C"], ["D"]]):
            section = TourSection(
                tour_translation=translation, title="Section", position=position
            )
            for content_position, text in enumerate(texts):
                session.add(
                    TourSectionContent(
                        tour_section=section,
                        position=content_position,
                        message_type=MessageType.text,
                        content={"text": text},
                    )
                )
        session.add(
            Subscription(
                guest=guest, tour=tour, expire_ts=datetime.now() + timedelta(days=1)
            )
        )
        await session.commit()

        return translation.id


@pytest.fixture
def application(db_engine: AsyncEngine):
    yield StubApplication(db_engine)

    ToursCommandHandler.cancel_all_running_sends()


async def add_delivery(
    db_engine: AsyncEngine,
    translation_id: int,
    section_position: int = 0,
    next_content_position: int = 1,
    age: timedelta = timedelta(),
):
    async with AsyncSession(db_engine) as session:
        session.add(
            TourDelivery(
                telegram_user_id=USER_ID,
                chat_id=USER_ID,
                tour_translation_id=translation_id,
                section_position=section_position,
                next_content_position=next_content_position,
                run_id="interrupted",
                updated_ts=datetime.now() - age,
            )
        )
        await session.commit()


async def get_delivery(db_engine: AsyncEngine) -> TourDelivery | None:
    async with AsyncSession(db_engine) as session:
        return await session.scalar(select(TourDelivery))


async def test_resumes_from_the_first_unsent_part(
    db_engine: AsyncEngine, application: StubApplication, translation_id: int
):
    await add_delivery(db_engine, translation_id)

    assert await application.resume() == ["B", "C", PROMPT]
    assert await get_delivery(db_engine) is None


async def test_stale_delivery_only_gets_the_prompt(
    db_engine: AsyncEngine, application: StubApplication, translation_id: int
):
    await add_delivery(db_engine, translation_id, age=timedelta(hours=2))

    assert await application.resume() == [PROMPT]
    assert await get_delivery(db_engine) is None


async def test_stale_last_section_is_dropped(
    db_engine: AsyncEngine, application: StubApplication, translation_id: int
):
    await add_delivery(
        db_engine,
        translation_id,
        section_position=1,
        next_content_position=0,
        age=timedelta(hours=2),
    )

    assert await application.resume() == []
    assert await get_delivery(db_engine) is None


async def test_expired_subscription_is_dropped(
    db_engine: AsyncEngine, application: StubApplication, translation_id: int
):
    await add_delivery(db_engine, translation_id)
    async with AsyncSession(db_engine) as session:
        subscription = await session.scalar(select(Subscription))
        subscription.expire_ts = datetime.now() - timedelta(minutes=1)
        await session.commit()

    assert await application.resume() == []
    assert await get_delivery(db_engine) is None


async def test_missing_section_is_dropped(
    db_engine: AsyncEngine, application: StubApplication, translation_id: int
):
    await add_delivery(db_engine, translation_id, section_position=5)

    assert await application.resume() == []
    assert await get_delivery(db_engine) is None


async def test_user_with_a_running_send_is_skipped(
    db_engine: AsyncEngine, application: StubApplication, translation_id: int
):
    await add_delivery(db_engine, translation_id)
    ToursCommandHandler.start_send(application, USER_ID, asyncio.sleep(60))

    await ToursCommandHandler.resume_deliveries(application)

    assert len(application.tasks) == 1, "Another send started for the user"
    assert (await get_delivery(db_engine)).run_id == "interrupted"


async def test_failed_part_is_skipped(
    db_engine: AsyncEngine, application: StubApplication, translation_id: int
):
    await add_delivery(db_engine, translation_id, next_content_position=0)
    application.bot.errors["B"] = [BadRequest("Can't parse entities")]

    assert await application.resume() == ["A", "C", PROMPT]
    assert await get_delivery(db_engine) is None


async def test_flood_limit_is_waited_out(
    db_engine: AsyncEngine, application: StubApplication, translation_id: int
):
    await add_delivery(db_engine, translation_id, next_content_position=0)
    application.bot.errors["B"] = [RetryAfter(0)]

    assert await application.resume() == ["A", "B", "C", PROMPT]


async def test_blocked_bot_stops_the_section(
    db_engine: AsyncEngine, application: StubApplication, translation_id: int
):
    await add_delivery(db_engine, translation_id, next_content_position=0)
    application.bot.errors["B"] = [Forbidden("Forbidden: bot was blocked by the user")]

    assert await application.resume() == ["A"]
    assert await get_delivery(db_engine) is None


async def test_progress_is_saved_after_each_part(
    db_engine: AsyncEngine, application: StubApplication, translation_id: int
):
    await add_delivery(db_engine, translation_id, next_content_position=0)
    application.bot.errors["B"] = [asyncio.CancelledError()]

    with pytest.raises(asyncio.CancelledError):
        await application.resume()

    assert application.bot.sent == ["A"]
    assert (await get_delivery(db_engine)).next_content_position == 1, (
        "The interrupted part must be sent again after a restart"
    )
