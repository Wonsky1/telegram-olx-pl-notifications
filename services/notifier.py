"""Background worker that checks for new OLX items and notifies users.

Single Responsibility: orchestrates *sending* notifications – it does not know
anything about Telegram handlers or database internals.  It depends only on
(1) an aiogram ``Bot`` instance for I/O and (2) the high-level
``MonitoringService`` abstraction for business queries.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Final

import pytz
from aiogram import Bot

from bot.responses import ITEMS_FOUND_CAPTION
from services.monitoring import MonitoringService

logger: Final = logging.getLogger(__name__)

# Warsaw timezone – kept here to avoid coupling with ``main.py``
WARSAW_TZ: Final = pytz.timezone("Europe/Warsaw")


def _now_warsaw() -> datetime:
    """Return current naive datetime in Europe/Warsaw timezone."""
    return datetime.now(timezone.utc).astimezone(WARSAW_TZ).replace(tzinfo=None)


class Notifier:  # noqa: D101 – simple name
    def __init__(self, bot: Bot, service: MonitoringService):
        self._bot = bot
        self._svc = service

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    async def run_periodically(
        self, interval_s: int
    ) -> None:  # noqa: D401 – simple name
        """Run background check forever sleeping *interval_s* between cycles."""
        while True:
            try:
                await self._check_and_send_items()
            except Exception:  # pragma: no cover – log unexpected
                logger.exception("Unexpected error during periodic check")
            logger.info("Sleeping for %s seconds", interval_s)
            await asyncio.sleep(interval_s)

    # ------------------------------------------------------------------
    # Internal helpers (should be small & testable)
    # ------------------------------------------------------------------
    async def _check_and_send_items(self) -> None:  # noqa: D401 – simple name
        """Check for new items and notify users."""
        pending_tasks = self._svc.pending_tasks()

        for task in pending_tasks:
            items_to_send = self._svc.items_to_send(task)
            logger.info(
                "Found %d items to send for chat_id %s",
                len(items_to_send),
                task.chat_id,
            )

            if not items_to_send:
                # Mark that we *did* check – useful for monitoring dashboards
                task.last_updated = _now_warsaw()
                continue

            # Notify user that N items were found
            await self._bot.send_photo(
                chat_id=task.chat_id,
                photo="https://tse4.mm.bing.net/th?id=OIG2.fso8nlFWoq9hafRkva2e&pid=ImgGn",
                caption=ITEMS_FOUND_CAPTION.format(
                    count=len(items_to_send), monitoring=task.name
                ),
            )

            for item in reversed(items_to_send):
                text = _format_item_text(item)
                if item.image_url:
                    await self._bot.send_photo(
                        chat_id=task.chat_id,
                        photo=item.image_url,
                        caption=text,
                        parse_mode="Markdown",
                    )
                else:
                    await self._bot.send_message(
                        chat_id=task.chat_id, text=text, parse_mode="Markdown"
                    )
                await asyncio.sleep(0.5)  # prevent Telegram Flood-wait

            # Persist bookkeeping timestamps
            self._svc.update_last_got_item(task.chat_id)
            task.last_updated = _now_warsaw()


# ---------------------------- Formatting helpers -----------------------------


def _format_item_text(item) -> str:  # type: ignore[annotation-unreachable]
    """Return Markdown-formatted text for *item* compatible with Telegram."""
    desc_lines = item.description.strip().split("\n")
    extra = {}
    for line in desc_lines:
        if line.startswith("price:"):
            extra["price_info"] = line.replace("price:", "Price:").strip()
        elif line.startswith("deposit:"):
            extra["deposit_info"] = line.replace("deposit:", "Deposit:").strip()
        elif line.startswith("animals_allowed:"):
            animals_allowed = line.replace("animals_allowed:", "").strip()
            if animals_allowed == "true":
                extra["animals_info"] = "Pets: Allowed"
            elif animals_allowed == "false":
                extra["animals_info"] = "Pets: Not allowed"
        elif line.startswith("rent:"):
            extra["rent_info"] = line.replace("rent:", "Additional rent:").strip()

    text = (
        f"📦 *{item.title}*\n\n"
        f"💰 *Price:* {item.price}\n"
        f"📍 *Location:* {item.location}\n"
        f"🕒 *Posted:* {item.created_at_pretty}\n"
    )
    # Optional extras
    if price := extra.get("price_info"):
        text += f"💵 *{price}* PLN\n"
    if (deposit := extra.get("deposit_info")) and deposit != "Deposit: 0":
        text += f"🔐 *{deposit}* PLN\n"
    if animals := extra.get("animals_info"):
        text += f"🐾 *{animals}*\n"
    if rent := extra.get("rent_info"):
        text += f"💳 *{rent}* PLN\n"

    text += f"🔗 [View on OLX]({item.link})"
    return text
