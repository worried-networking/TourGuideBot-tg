# Tour Guide Bot [telegram]

[![Crowdin](https://badges.crowdin.net/tourguidebot/localized.svg)](https://crowdin.com/project/tourguidebot)

Project allows you to create, manage and share virtual guided tours,
viewable over Telegram.

Guests get access to a tour either by paying for it through Telegram Payments
(once you configure a payment provider and add prices) or by being approved
manually from the admin mode. Guests are identified by phone number, so you
can approve somebody before they have ever opened the bot.

See [CONTEXT.md](CONTEXT.md) for the project's vocabulary.

## Bot commands

The bot is a single Telegram bot with two modes. Everybody starts in guest
mode; admins switch to admin mode with `/admin` and back with `/guest`.

### Guest mode (default)

* `/start` — initialize the bot. It will greet you, ask for the phone number
             and check if you have any tours available.
* `/tours` — list the available tours and start one of them.
* `/purchase` — buy access to a tour (shown only when at least one price is
                configured).
* `/terms` — show the terms message (shown only when it is configured).
* `/support` — show the support message (shown only when it is configured).
* `/language` — change the interface language.
* `/help` — show the available commands.
* `/admin` — switch to the admin mode (admins only).

### Admin mode

* `/guest` — exit the admin mode.
* `/tours` — manage your tours: translations, sections, content and prices.
* `/approve` — allow a phone number to access a tour for a number of days.
* `/revoke` — revoke access to a tour.
* `/configure` — change the bot's settings: welcome, terms and support
                 messages, payment providers, audio-to-voice conversion,
                 content protection and the delay between messages.
* `/language` — change the interface language.
* `/help` — show the available commands.

To become the first admin, send `/admin`, share your phone number and then
send the md5 hash of the bot token when asked. Afterwards the phone number is
trusted.

## Running

### Preparation

First of all you need to register a bot with [BotFather](https://t.me/BotFather).

Have the received token ready and don't share it anywhere.

### Database

The easiest way to run the bot is by using a sqlite3 database, but it's not
recommended if you expect multiple users at the same time. The example of
how to run the bot with this DB is in the next section.

Keep in mind, that the database connection URL must be in the SQLAlchemy format,
see the [documentation](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls)
for further details. Also note that you need to provide an async dialect for
the connection, e.g. aiosqlite, asyncpg or aiomysql.

### Simplest way to run (recommended only for development or testing purposes)

```shell
docker run --restart=unless-stopped -d \
    -v $(pwd)/persistent:/home/tg/app/persistent \
    ghcr.io/andrey-yantsen/tourguidebot-tg:latest \
        -g <telegram_bot_token> \
        --db=sqlite+aiosqlite:////home/tg/app/persistent/tour_guide_bot.sqlite3
```

Do not forget to replace `<telegram_bot_token>` with the correct token value.

This starts the bot against a sqlite database stored in the mounted
`persistent` directory, which also holds the bot's conversation state.

### Recommended way

Copy included `docker-compose.yml.example` into `docker-compose.yml`, and
replace `<telegram_bot_token>` with the correct token value.

After that, you should be able to start everything required with the following
command:

```shell
docker compose up
```

### Optional web admin panel

Pass `--enable-http-server` to also serve a small admin panel (default
`0.0.0.0:8080`, see `--http-host` and `--http-port`). It requires
`--http-cookie-key`; run once without it and the bot prints a freshly
generated key to use. Admins log in through the Telegram Login widget, so the
bot's domain must be registered with BotFather (`/setdomain`).

## Contributing

In order to run the tests you'll need to have:

* A telegram bot token
* A telegram app api_id and api_hash (from https://my.telegram.org/apps)
* A session string for the app; you can get one by executing the code below:

```python
from telethon import TelegramClient
from telethon.sessions import StringSession


api_id = "YOUR API ID"
api_hash = "YOUR API HASH"


with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("Session string:", client.session.save())
```

Thanks to [ShallowDepth](https://shallowdepth.online/posts/2021/12/end-to-end-tests-for-telegram-bots/) for the instructions.
