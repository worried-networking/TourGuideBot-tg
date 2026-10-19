import asyncio
from datetime import datetime, timedelta
from os import environ
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.custom.conversation import Conversation
from telethon.tl.types import KeyboardButtonRequestPhone

from tour_guide_bot.bot.app import Application
from tour_guide_bot.cli import prepare_app
from tour_guide_bot.helpers.currency import Currency
from tour_guide_bot.models.admin import Admin, AdminPermissions
from tour_guide_bot.models.guide import (
    Guest,
    MessageType,
    Product,
    Subscription,
    Tour,
    TourSection,
    TourSectionContent,
    TourTranslation,
)
from tour_guide_bot.models.settings import PaymentProvider, Settings, SettingsKey
from tour_guide_bot.models.telegram import TelegramUser


@pytest.fixture(scope="session")
def bot_token() -> str:
    token = environ.get("TOUR_GUIDE_TELEGRAM_BOT_TOKEN")
    assert token, (
        "Please set the telegram bot token via TOUR_GUIDE_TELEGRAM_BOT_TOKEN env variable"
    )
    return token


@pytest.fixture(scope="session")
def mtproto_api_id():
    api_id = environ.get("TOUR_GUIDE_TELEGRAM_APP_API_ID")
    assert api_id, (
        "Please set the telegram app api id via TOUR_GUIDE_TELEGRAM_APP_API_ID env variable"
    )
    return api_id


@pytest.fixture(scope="session")
def mtproto_api_hash():
    api_hash = environ.get("TOUR_GUIDE_TELEGRAM_APP_API_HASH")
    assert api_hash, (
        "Please set the telegram app api hash via TOUR_GUIDE_TELEGRAM_APP_API_HASH env variable"
    )
    return api_hash


@pytest.fixture(scope="session")
def payment_token() -> str:
    token = environ.get("TOUR_GUIDE_TELEGRAM_PAYMENT_TOKEN")

    if not token:
        pytest.skip(
            "No payment token found in TOUR_GUIDE_TELEGRAM_PAYMENT_TOKEN env variable"
        )

    return token


@pytest.fixture(scope="session")
def mtproto_session_string() -> StringSession:
    session_string = environ.get("TOUR_GUIDE_TELEGRAM_APP_SESSION_STRING")

    assert session_string, (
        "Please set the telegram app session string via TOUR_GUIDE_TELEGRAM_APP_SESSION_STRING env variable (see readme on how to get it)"
    )
    return StringSession(session_string)


@pytest.fixture
def persistence_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("persistence")


@pytest.fixture
def test_db_file(persistence_path: Path) -> Path:
    return persistence_path.joinpath("test.db")


@pytest.fixture
async def db_engine(test_db_file: Path):
    import tour_guide_bot.models.admin as _admin  # noqa: F401
    import tour_guide_bot.models.guide as _guite  # noqa: F401
    import tour_guide_bot.models.settings as _settings  # noqa: F401
    import tour_guide_bot.models.telegram as _telegram  # noqa: F401
    from tour_guide_bot.models import Base

    engine = create_async_engine("sqlite+aiosqlite:///{}".format(test_db_file))

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield engine


@pytest.fixture
def enabled_languages(request: pytest.FixtureRequest) -> list[str]:
    marker = request.node.get_closest_marker("enabled_languages")
    if marker is None:
        data = ["en", "ru"]
    else:
        data = marker.args

    return data


@pytest.fixture
def products_count_in_default_tour(request: pytest.FixtureRequest) -> int:
    marker = request.node.get_closest_marker("products_count_in_default_tour")
    if marker is None:
        return 1

    return marker.args[0]


@pytest.fixture
def default_tour(
    products_count_in_default_tour: int, enabled_languages: list[str]
) -> dict:
    return {
        "products": [
            {
                "currency": "USD",
                "payment_provider_id": 1,
                "price": int(100 * (1 + 0.2 * i)),
                "duration_days": i + 1,
                "guests": 1,
            }
            for i in range(products_count_in_default_tour)
        ],
        "translations": {
            lang: {
                "title": "Test tour {}".format(lang),
                "description": "Test tour description {}.".format(lang),
                "sections": [
                    {
                        "title": "Test section 1 {}".format(lang),
                        "content": [
                            {
                                "type": MessageType.text,
                                "content": {"text": "Test text 1 {}".format(lang)},
                            },
                            {
                                "type": MessageType.location,
                                "content": {
                                    "latitude": 51.5072046,
                                    "longitude": -0.1758395,
                                },
                            },
                            {
                                "type": MessageType.text,
                                "content": {"text": "Test text 2 {}".format(lang)},
                            },
                        ],
                    },
                    {
                        "title": "Test section 2 {}".format(lang),
                        "content": [
                            {
                                "type": MessageType.text,
                                "content": {"text": "Test text 3 {}".format(lang)},
                            },
                            {
                                "type": MessageType.text,
                                "content": {"text": "Test text 4 {}".format(lang)},
                            },
                        ],
                    },
                ],
            }
            for lang in enabled_languages
        },
    }


@pytest.fixture
async def tours_as_dicts(
    request: pytest.FixtureRequest, default_tour: dict
) -> list[dict]:
    marker = request.node.get_closest_marker("tours")
    if marker is None:
        tours = [default_tour]
    else:
        tours = marker.args

    return tours


@pytest.fixture
async def tours(
    request: pytest.FixtureRequest,
    db_engine: AsyncEngine,
    tours_as_dicts: list[dict],
    conversation: Conversation,
) -> list[Tour]:
    cached_files = {}

    ret = []

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        for tour in tours_as_dicts:
            tour_model = Tour()
            session.add(tour_model)

            for lang, data in tour.get("translations", {}).items():
                tour_translation = TourTranslation(
                    language=lang,
                    tour=tour_model,
                    title=data["title"],
                    description=data["description"],
                )
                session.add(tour_translation)

                for idx, section in enumerate(data["sections"]):
                    tour_section = TourSection(
                        tour_translation=tour_translation,
                        title=section["title"],
                        position=idx,
                    )
                    session.add(tour_section)

                    for content_idx, content in enumerate(section["content"]):
                        for file in content["content"].get("files", []):
                            file_to_upload = file.pop("file", None)
                            if file_to_upload:
                                if file_to_upload in cached_files:
                                    uploaded = await conversation.send_file(
                                        file_to_upload
                                    )
                                    cached_files[file_to_upload] = uploaded["file_id"]
                                file["file_id"] = cached_files[file_to_upload]

                        content = TourSectionContent(
                            message_type=content["type"],
                            tour_section=tour_section,
                            position=content_idx,
                            media_group_id=content.get("media_group_id"),
                            content=content["content"],
                        )
                        session.add(content)

                skip_payment_token_stub = request.node.get_closest_marker(
                    "skip_payment_token_stub"
                )

                skip_adding_products = request.node.get_closest_marker(
                    "skip_adding_products"
                )

                if skip_payment_token_stub is None and skip_adding_products is None:
                    for product_config in tour.get("products", []):
                        product = Product(
                            tour=tour_model,
                            language=lang,
                            title=data["title"],
                            description=f"Buy {product_config['duration_days']} day(s) acess to {data['title']} for {product_config['guests']} guest(s)",
                            **product_config,
                        )
                        session.add(product)

            ret.append(tour_model)

        await session.commit()

    return ret


@pytest.fixture
async def approved_tours(
    request: pytest.FixtureRequest,
    db_engine: AsyncEngine,
    guest: Guest,
    tours: list[Tour],
):
    marker = request.node.get_closest_marker("approved_tour_ids")
    approved_tour_ids = None
    if marker is not None:
        approved_tour_ids = marker.args

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        for tour in tours:
            if approved_tour_ids is None or tour.id in approved_tour_ids:
                purchase = Subscription(
                    guest=guest,
                    tour=tour,
                    expire_ts=datetime.now() + timedelta(minutes=10),
                )
                session.add(purchase)

        await session.commit()


@pytest.fixture
def default_language() -> str:
    return "en"


@pytest.fixture
def unitialized_app(
    bot_token: str,
    db_engine: AsyncEngine,
    enabled_languages: list[str],
    default_language: str,
    persistence_path: Path,
):
    app = prepare_app(
        bot_token, db_engine, enabled_languages, default_language, str(persistence_path)
    )

    yield app


@pytest.fixture
async def unconfigured_app(unitialized_app: Application):
    await unitialized_app.initialize()
    if unitialized_app.post_init:
        await unitialized_app.post_init(unitialized_app)
    await unitialized_app.updater.start_polling()
    await unitialized_app.start()

    yield unitialized_app

    try:
        if unitialized_app.updater.running:
            await unitialized_app.updater.stop()
    except:
        pass

    try:
        if unitialized_app.running:
            await unitialized_app.stop()

        if unitialized_app.post_stop:
            await unitialized_app.post_stop(unitialized_app)

        await unitialized_app.shutdown()

        if unitialized_app.post_shutdown:
            await unitialized_app.post_shutdown(unitialized_app)
    except:
        pass
    finally:
        await asyncio.sleep(2)


@pytest.fixture
async def app(
    request: pytest.FixtureRequest,
    unconfigured_app: Application,
    db_engine: AsyncEngine,
    enabled_languages: list[str],
):
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        for lang in enabled_languages:
            welcome_message = Settings(
                key=SettingsKey.guide_welcome_message,
                language=lang,
                value=r"welcome \(%s\)" % lang,
            )
            session.add(welcome_message)

            terms = Settings(
                key=SettingsKey.terms_message,
                language=lang,
                value=r"terms \(%s\)" % lang,
            )
            session.add(terms)

            support = Settings(
                key=SettingsKey.support_message,
                language=lang,
                value=r"support \(%s\)" % lang,
            )
            session.add(support)

        skip_payment_token_stub = request.node.get_closest_marker(
            "skip_payment_token_stub"
        )
        if skip_payment_token_stub is None:
            payment_tokens_count = request.node.get_closest_marker(
                "payment_tokens_count"
            )
            assert payment_tokens_count is None or len(payment_tokens_count.args) == 1
            cnt = (
                1 if payment_tokens_count is None else int(payment_tokens_count.args[0])
            )

            for i in range(int(cnt)):
                provider = PaymentProvider(
                    name="test provider {}".format(i + 1),
                    config={"token": "fake_token {}".format(i + 1)},
                    enabled=True,
                )
                session.add(provider)

        await session.commit()

    yield unconfigured_app


@pytest.fixture
async def payment_provider(db_engine: AsyncEngine, payment_token: str):
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        stmt = select(PaymentProvider).where(PaymentProvider.enabled == True)
        provider: PaymentProvider | None = await session.scalar(stmt)

        if provider is None:
            provider = PaymentProvider(
                name="test provider", config={"token": payment_token}, enabled=True
            )
        else:
            provider.config = {"token": payment_token}

        session.add(provider)

        await session.commit()

    return payment_token


@pytest.fixture
async def telegram_client(
    mtproto_api_id: str, mtproto_api_hash: str, mtproto_session_string: StringSession
):
    client = TelegramClient(
        mtproto_session_string,
        mtproto_api_id,
        mtproto_api_hash,
        sequential_updates=True,
        flood_sleep_threshold=60,
    )
    await client.connect()
    await client.get_me()
    await client.get_dialogs()

    yield client

    await client.disconnect()
    await client.disconnected


@pytest.fixture(scope="session")
def bot_id(bot_token: str) -> int:
    return int(bot_token.split(":")[0])


class ConversationWrapper:
    def __init__(self, wrappee: Conversation):
        self.wrappee = wrappee

    def __getattr__(self, attr):
        return getattr(self.wrappee, attr)

    async def send_message(self, *args, **kwargs):
        ret = await self.wrappee.send_message(*args, **kwargs)
        await asyncio.sleep(1)
        return ret

    async def send_file(self, *args, **kwargs):
        ret = await self.wrappee.send_file(*args, **kwargs)
        await asyncio.sleep(1)
        return ret

    async def wait_event(self, event, *, timeout=None):
        ret = await self.wrappee.wait_event(event, timeout=timeout)
        await asyncio.sleep(1)
        return ret


@pytest.fixture
async def conversation(telegram_client: TelegramClient, bot_id: int):
    async with telegram_client.conversation(
        bot_id, timeout=10, max_messages=10000
    ) as conv:
        yield ConversationWrapper(conv)


async def get_telegram_user(
    user_id: int, language: str, session: AsyncSession
) -> TelegramUser:
    stmt = (
        select(TelegramUser)
        .where(TelegramUser.id == user_id)
        .options(selectinload(TelegramUser.admin), selectinload(TelegramUser.guest))
    )
    user: TelegramUser | None = await session.scalar(stmt)

    if not user:
        user = TelegramUser(id=user_id, language=language)

    return user


@pytest.fixture
async def guest(
    db_engine: AsyncEngine, telegram_client: TelegramClient, default_language: str
):
    me = await telegram_client.get_me()
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        guest = Guest(phone=me.phone)
        telegram_user = await get_telegram_user(me.id, default_language, session)
        telegram_user.guest = guest

        session.add(guest)
        session.add(telegram_user)
        await session.commit()

        return guest


@pytest.fixture
async def admin(
    db_engine: AsyncEngine,
    telegram_client: TelegramClient,
    default_language: str,
):
    me = await telegram_client.get_me()
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        admin = Admin(phone=me.phone, permissions=AdminPermissions.full)
        telegram_user = await get_telegram_user(me.id, default_language, session)
        telegram_user.admin = admin

        session.add(admin)
        session.add(telegram_user)
        await session.commit()

        return admin


@pytest.fixture
async def admin_conversation(conversation: Conversation, unconfigured_app, admin):
    await conversation.send_message("/admin")
    response = await conversation.get_response()

    assert "Welcome to the admin mode" in response.message, (
        "Unexpected message in response to the admin mode switch"
    )

    await asyncio.sleep(0.5)

    yield conversation


async def get_phone_number_request(conversation: Conversation):
    response = await conversation.get_response()
    assert response.reply_markup is not None, "No reply markup"
    assert response.reply_markup.rows, "No reply markup rows"
    assert response.reply_markup.rows[0].buttons, "No reply markup buttons"
    assert isinstance(
        response.reply_markup.rows[0].buttons[0], KeyboardButtonRequestPhone
    ), "No request phone button"
    return response


async def get_currency_config():
    return {
        "AED": {
            "code": "AED",
            "title": "United Arab Emirates Dirham",
            "symbol": "AED",
            "native": "د.إ.‏",
            "thousands_sep": ",",
            "decimal_sep": ".",
            "symbol_left": True,
            "space_between": True,
            "exp": 2,
            "min_amount": "367",
            "max_amount": "3672304",
        },
        "USD": {
            "code": "USD",
            "title": "United States Dollar",
            "symbol": "$",
            "native": "$",
            "thousands_sep": ",",
            "decimal_sep": ".",
            "symbol_left": True,
            "space_between": False,
            "exp": 2,
            "min_amount": "100",
            "max_amount": 1000000,
        },
        "CLP": {
            "code": "CLP",
            "title": "Chilean Peso",
            "symbol": "CLP",
            "native": "$",
            "thousands_sep": ".",
            "decimal_sep": ",",
            "symbol_left": False,
            "space_between": True,
            "exp": 0,
            "min_amount": "794",
            "max_amount": "7942624",
        },
        "XXX": {
            "code": "XXX",
            "title": "Chilean Peso",
            "symbol": "XXX",
            "native": "$",
            "thousands_sep": ".",
            "decimal_sep": ",",
            "symbol_left": False,
            "space_between": False,
            "exp": 0,
            "min_amount": "794",
            "max_amount": "7942624",
        },
    }


@pytest.fixture
async def mock_currency_config(mocker: MockerFixture):
    Currency.cache = None
    Currency.last_cache_update = None
    mocker.patch.object(Currency, "load_currencies_config", new=get_currency_config)
