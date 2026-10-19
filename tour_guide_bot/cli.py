import argparse
import asyncio
import logging
import signal
import sys
from os import mkdir, sep
from os.path import dirname, realpath
from warnings import filterwarnings

import aiohttp_jinja2
import aiohttp_session
import jinja2
from aiohttp import web
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from telegram.ext import PicklePersistence
from telegram.warnings import PTBUserWarning

from tour_guide_bot import log, set_fallback_locale, t
from tour_guide_bot.bot.app import Application
from tour_guide_bot.web import routes


def prepare_app(
    guide_bot_token: str,
    engine: AsyncEngine,
    enabled_languages: list[str],
    default_language: str,
    persistence_path: str,
    application_class=Application,
) -> Application:
    filterwarnings(
        action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning
    )

    app = (
        application_class.builder()
        .token(guide_bot_token)
        .concurrent_updates(True)
        .build()
    )
    app.content_add_lock = asyncio.Lock()
    app.db_engine = engine
    app.enabled_languages = enabled_languages
    app.default_language = default_language
    app.persistence = PicklePersistence(
        persistence_path + sep + "telegram_guide_bot_storage.pickle", update_interval=30
    )

    return app


def run():
    parser = argparse.ArgumentParser(
        description=t().pgettext("cli", "Tour Guide bot [telegram]")
    )
    parser.add_argument(
        "--debug",
        "-d",
        help=t().pgettext("cli", "Enable debug logging."),
        action="store_true",
    )
    parser.add_argument(
        "--enabled-languages",
        help=t().pgettext("cli", "Comma-separated list of available languages."),
        default="en",
        type=lambda s: [item.strip() for item in s.split(",")],
    )
    parser.add_argument(
        "--default-language",
        "-l",
        help=t().pgettext(
            "cli",
            "Default language. If not provided, will be set to the first enabled language.",
        ),
        default=None,
        type=str,
    )
    parser.add_argument(
        "--guide-bot-token",
        "-g",
        help=t().pgettext("cli", "Telegram Bot token for the Guide Bot."),
        type=str,
        required=True,
    )
    parser.add_argument(
        "--db",
        help=t().pgettext("cli", "SQLAlchemy engine URL"),
        type=str,
        required=True,
    )
    parser.add_argument(
        "--enable-http-server",
        help=t().pgettext("cli", "Enable HTTP server."),
        action="store_true",
    )
    parser.add_argument(
        "--http-host",
        help=t().pgettext("cli", "HTTP-server host."),
        default="0.0.0.0",
        type=str,
    )
    parser.add_argument(
        "--http-port",
        help=t().pgettext("cli", "HTTP-server port."),
        default=8080,
        type=int,
    )
    parser.add_argument(
        "--http-cookie-key",
        help=t().pgettext("cli", "Cookie encryption key."),
        type=str,
    )

    args = parser.parse_args()

    if args.enable_http_server and not args.http_cookie_key:
        fernet_key = fernet.Fernet.generate_key()
        print(
            t()
            .pgettext(
                "cli",
                "You need to provide a cookie encryption key for the HTTP server to work. "
                "Please re-run the server providing argument --http-cookie-key='{}'",
            )
            .format(fernet_key.decode("ascii"))
        )
        exit(1)

    if len(args.enabled_languages) == 0:
        parser.error(
            t().pgettext("cli", "the list of enabled languages must not be empty")
        )

    if args.default_language is None:
        args.default_language = args.enabled_languages[0]

    if args.default_language not in args.enabled_languages:
        parser.error(
            t().pgettext(
                "cli", "the default language must be in the list of enabled languages"
            )
        )

    set_fallback_locale(args.default_language)

    log.setLevel(logging.INFO)
    if args.debug:
        log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] [%(module)s:%(lineno)d] %(message)s"
        log.setLevel(logging.DEBUG)
    else:
        log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S"))
    log.addHandler(handler)

    engine = create_async_engine(args.db)

    loop = asyncio.new_event_loop()

    parent_path = dirname(dirname(__file__))
    destination_path = parent_path + sep + "persistent"

    try:
        mkdir(destination_path)
    except OSError:
        pass

    app = prepare_app(
        args.guide_bot_token,
        engine,
        args.enabled_languages,
        args.default_language,
        destination_path,
    )

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, loop.stop)

    loop.run_until_complete(app.initialize())
    if app.post_init:
        loop.run_until_complete(app.post_init(app))
    loop.run_until_complete(app.updater.start_polling())
    loop.run_until_complete(app.start())

    if args.enable_http_server:
        web_path = dirname(realpath(__file__)) + "/web/"
        webapp = web.Application()

        for static_path in ("js", "css"):
            webapp.add_routes(
                [web.static(f"/{static_path}", f"{web_path}static/{static_path}")]
            )

        aiohttp_session.setup(webapp, EncryptedCookieStorage(args.http_cookie_key))

        async def add_layout_data_to_context(request):
            session = await aiohttp_session.get_session(request)
            return {
                "bot_info": request.app.bot_user_info,
                "user_info": session.get("user_info"),
                "current_page": request.path,
                "default_language": request.app.default_language,
                "enabled_languages": request.app.enabled_languages,
            }

        jinja_env = aiohttp_jinja2.setup(
            webapp,
            loader=jinja2.FileSystemLoader(web_path + "templates"),
            extensions=["jinja2.ext.i18n"],
            context_processors=[add_layout_data_to_context],
        )
        jinja_env.install_gettext_translations(t(args.default_language), newstyle=True)

        webapp.bot_user_info = loop.run_until_complete(app.bot.get_me())
        webapp.bot = app.bot
        webapp.default_language = args.default_language
        webapp.enabled_languages = args.enabled_languages
        webapp.db_engine = engine

        webapp.add_routes(routes)

        # web.run_app() would cancel the bot's tasks and close the loop on exit
        web_runner = web.AppRunner(webapp)
        loop.run_until_complete(web_runner.setup())
        loop.run_until_complete(
            web.TCPSite(web_runner, args.http_host, args.http_port).start()
        )
    else:
        web_runner = None

    try:
        log.info(t().pgettext("cli", "Up and runnig!"))
        loop.run_forever()
    finally:
        if web_runner:
            loop.run_until_complete(web_runner.cleanup())

        # Application.stop() writes the pending changes to the persistence
        loop.run_until_complete(app.updater.stop())
        loop.run_until_complete(app.stop())
        loop.run_until_complete(app.shutdown())
        loop.close()


if __name__ == "__main__":
    run()
