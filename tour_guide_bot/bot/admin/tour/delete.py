from typing import ClassVar

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tour_guide_bot import t
from tour_guide_bot.helpers.telegram import SubcommandHandler, get_tour_title
from tour_guide_bot.helpers.tours_selector import SelectTourHandler
from tour_guide_bot.models.guide import Tour, TourDelivery


class DeleteHandler(SubcommandHandler, SelectTourHandler):
    STATE_AWAITING_CONFIRMATION: ClassVar[int] = 2

    @classmethod
    def get_handlers(cls):
        return [
            ConversationHandler(
                entry_points=[
                    CallbackQueryHandler(
                        cls.partial(cls.send_tour_selector),
                        cls.get_callback_data_pattern(),
                    ),
                ],
                states={
                    cls.STATE_SELECT_TOUR: cls.get_select_tour_handlers(),
                    cls.STATE_AWAITING_CONFIRMATION: [
                        CallbackQueryHandler(
                            cls.partial(cls.delete_tour),
                            cls.get_callback_data_pattern(r"(\d+)"),
                        ),
                        CallbackQueryHandler(
                            cls.partial(cls.cancel),
                            cls.get_callback_data_pattern(r"cancel"),
                        ),
                    ],
                },
                fallbacks=[
                    CommandHandler("cancel", cls.partial(cls.cancel)),
                    CallbackQueryHandler(cls.partial(cls.cancel), "cancel"),
                    MessageHandler(filters.COMMAND, cls.partial(cls.unknown_command)),
                    MessageHandler(filters.ALL, cls.partial(cls.unexpected_message)),
                ],
                name="admin-delete-tour",
                persistent=True,
            )
        ]

    @staticmethod
    def get_name(language: str) -> str:
        return t(language).pgettext("admin-tour", "Delete a tour")

    async def after_tour_selected(
        self,
        tour: Tour,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        is_single_tour: bool,
    ):
        language = await self.get_language(update, context)

        await update.callback_query.edit_message_text(
            t(language)
            .pgettext("admin-tours", 'Do you really want to delete the tour "{0}"?')
            .format(get_tour_title(tour, language, context)),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            t(language).pgettext("bot-generic", "Yes"),
                            callback_data=self.get_callback_data(tour.id),
                        ),
                        InlineKeyboardButton(
                            t(language).pgettext("bot-generic", "Abort"),
                            callback_data=self.get_callback_data("cancel"),
                        ),
                    ],
                ]
            ),
        )

        return self.STATE_AWAITING_CONFIRMATION

    async def delete_tour(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):
        user = await self.get_user(update, context)
        tour: Tour | None = await self.db_session.scalar(
            select(Tour)
            .where(Tour.id == context.matches[0].group(1))
            .options(selectinload(Tour.translations))
        )

        if not tour:
            await update.callback_query.answer()
            await self.edit_or_reply_text(
                update,
                context,
                t(user.language).pgettext(
                    "bot-generic", "Something went wrong; please try again."
                ),
            )
            return ConversationHandler.END

        tour_title = get_tour_title(tour, user.language, context)

        await self.db_session.execute(
            delete(TourDelivery).where(
                TourDelivery.tour_translation_id.in_(
                    [translation.id for translation in tour.translations]
                )
            )
        )
        await self.db_session.delete(tour)
        await self.db_session.commit()

        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            t(user.language)
            .pgettext("admin-tours", 'The tour "{0}" was removed.')
            .format(tour_title)
        )
        return ConversationHandler.END

    def get_tour_selection_message(self, language: str) -> str:
        return t(language).pgettext(
            "admin-tour", "Please select the tour you want to delete."
        )

    @classmethod
    async def is_available(cls, db_session: AsyncSession) -> bool:
        tours_count: int = await db_session.scalar(select(func.count(Tour.id)))
        return tours_count > 0
