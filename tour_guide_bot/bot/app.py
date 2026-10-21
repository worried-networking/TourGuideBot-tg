from asyncio import create_task
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from telegram import Update
from telegram.ext import Application as BaseApplication
from telegram.ext import ApplicationBuilder, ContextTypes, TypeHandler

from tour_guide_bot import t
from tour_guide_bot.bot import log
from tour_guide_bot.bot.admin.start import (
    StartCommandHandler as AdminStartCommandHandler,
)
from tour_guide_bot.bot.guide.help import HelpCommandHandler
from tour_guide_bot.bot.guide.purchase import PurchaseCommandHandler
from tour_guide_bot.bot.guide.start import StartCommandHandler
from tour_guide_bot.bot.guide.tours import ToursCommandHandler
from tour_guide_bot.helpers.language import LanguageHandler
from tour_guide_bot.helpers.telegram import get_tour_title
from tour_guide_bot.models.guide import Guest, Subscription, Tour
from tour_guide_bot.models.telegram import TelegramUser


class Application(BaseApplication):
    @classmethod
    def builder(cls) -> ApplicationBuilder:
        builder = super().builder()
        builder.application_class(cls)
        return builder

    async def initialize(self) -> None:
        self.add_handler(TypeHandler(object, self.debug_log_handler), -1)

        self.add_handlers(AdminStartCommandHandler.get_handlers())

        self.add_handlers(StartCommandHandler.get_handlers())
        self.add_handlers(ToursCommandHandler.get_handlers())
        self.add_handlers(PurchaseCommandHandler.get_handlers())
        self.add_handlers(LanguageHandler.get_handlers())
        self.add_handlers(HelpCommandHandler.get_handlers())

        self.job_queue.run_repeating(
            self.check_new_approved_tours, 60, job_kwargs={"misfire_grace_time": 30}
        )

        await super().initialize()

    async def start(self) -> None:
        await super().start()
        self.create_task(ToursCommandHandler.resume_deliveries(self))

    async def stop(self) -> None:
        # stop() awaits the background tasks before saving the persistence, a
        # half-sent tour section mustn't hold the shutdown up
        cancel_sends = create_task(self.cancel_sends_after_updates())
        await super().stop()
        await cancel_sends

    async def cancel_sends_after_updates(self) -> None:
        # Updates still in the queue can start new sends
        await self.update_queue.join()
        ToursCommandHandler.cancel_all_running_sends()

    async def debug_log_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        log.debug(
            "[{0}] received update: {1}".format(
                context.application.__class__.__name__, update
            )
        )

    async def check_new_approved_tours(
        self, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        # TODO: Improve the logic
        # Currently this may send an incorrect notification when a guest would have multiple
        # telegram users.
        stmt = (
            select(TelegramUser)
            .join(Guest)
            .join(Subscription, Guest.id == Subscription.guest_id)
            .where(Subscription.is_user_notified == False)  # noqa
        )

        async with AsyncSession(
            context.application.db_engine, expire_on_commit=False
        ) as session:
            for telegram_user in await session.scalars(stmt):
                stmt = (
                    select(Subscription)
                    .options(
                        selectinload(Subscription.tour).selectinload(Tour.translations),
                        selectinload(Subscription.guest),
                    )
                    .where(
                        (Subscription.guest_id == telegram_user.guest_id)
                        & (Subscription.is_user_notified == False)  # noqa
                    )
                )
                bought_tours: Sequence[Subscription] = (
                    await session.scalars(stmt)
                ).all()
                for purchase in bought_tours:
                    language = telegram_user.language

                    await self.bot.send_message(
                        telegram_user.id,
                        t(language)
                        .pgettext(
                            "guide-bot-notification",
                            'Hey! You have a new tour available — "{0}". Send /tours to start the journey!',
                        )
                        .format(get_tour_title(purchase.tour, language, context)),
                    )

                    purchase.is_user_notified = True
                    session.add(purchase)
                    await session.commit()
