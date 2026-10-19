import asyncio
from collections.abc import Awaitable
from typing import Any

from telegram import Update
from telegram.ext import BaseUpdateProcessor


class PerUserUpdateProcessor(BaseUpdateProcessor):
    """Runs updates of the same user sequentially and different users concurrently.

    Conversation state is stored only after a callback returns, so a user's next
    update must not start before the previous one is finished.
    """

    def __init__(self, max_concurrent_updates: int):
        super().__init__(max_concurrent_updates)
        # key -> [lock, holders + waiters]
        self._locks: dict[int, list[Any]] = {}

    @staticmethod
    def _key(update: object) -> int | None:
        if not isinstance(update, Update) or update.pre_checkout_query:
            # pre_checkout_query must be answered within 10s, never queue it
            return None
        if update.effective_user:
            return update.effective_user.id
        if update.effective_chat:
            return update.effective_chat.id
        return None

    # BaseUpdateProcessor.process_update is only marked @final for type checkers.
    # We override it to take the per-user lock before the global semaphore, so
    # queued updates of one user don't occupy global slots.
    async def process_update(  # type: ignore[misc]
        self, update: object, coroutine: Awaitable[Any]
    ) -> None:
        key = self._key(update)
        if key is None:
            await super().process_update(update, coroutine)
            return

        entry = self._locks.setdefault(key, [asyncio.Lock(), 0])
        entry[1] += 1
        try:
            async with entry[0]:
                await super().process_update(update, coroutine)
        finally:
            entry[1] -= 1
            if entry[1] == 0:
                del self._locks[key]

    async def do_process_update(
        self, update: object, coroutine: Awaitable[Any]
    ) -> None:
        await coroutine

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass
