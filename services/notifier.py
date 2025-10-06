"""Background worker that checks for new OLX items and notifies users.

Single Responsibility: orchestrates *sending* notifications – it does not know
anything about Telegram handlers or database internals.  It depends only on
(1) an aiogram ``Bot`` instance for I/O and (2) the high-level
``MonitoringService`` abstraction for business queries.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Final

from aiogram import Bot

from bot.responses import ITEMS_FOUND_CAPTION
from services.monitoring import MonitoringService

logger: Final = logging.getLogger(__name__)


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
        pending_tasks = await self._svc.pending_tasks()

        for task in pending_tasks:
            items_to_send = await self._svc.items_to_send(task)
            logger.info(
                "Found %d items to send for chat_id %s",
                len(items_to_send),
                task.chat_id,
            )

            if not items_to_send:
                # Mark that we *did* check – useful for monitoring dashboards
                await self._svc.update_last_updated(task)
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
                # Handle both dict and object access patterns for image_url
                image_url = (
                    item.get("image_url")
                    if isinstance(item, dict)
                    else getattr(item, "image_url", None)
                )
                if image_url:
                    await self._bot.send_photo(
                        chat_id=task.chat_id,
                        photo=image_url,
                        caption=text,
                        parse_mode="MarkdownV2",
                    )
                else:
                    await self._bot.send_message(
                        chat_id=task.chat_id, text=text, parse_mode="MarkdownV2"
                    )
                await asyncio.sleep(0.5)  # prevent Telegram Flood-wait

            # Persist bookkeeping timestamps
            await self._svc.update_last_got_item(task.chat_id)
            await self._svc.update_last_updated(task)


# ---------------------------- Formatting helpers -----------------------------


def _escape_markdown_v2(text: str) -> str:
    """
    Escape all special characters for Telegram MarkdownV2.
    """
    if not text:
        return text
    # All special characters that need escaping in MarkdownV2
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    for char in escape_chars:
        text = text.replace(char, rf"\{char}")
    return text


def bold_telegram_md(text: str) -> str:
    """
    Safely wrap user content in *...* for Telegram MarkdownV2.
    Escapes all special characters before wrapping.
    """
    if not text:
        return ""
    text = _escape_markdown_v2(text)
    return f"*{text}*"


def _format_item_text(item) -> str:  # type: ignore[annotation-unreachable]
    """Return Markdown-formatted text for *item* compatible with Telegram."""
    # Handle both dict and object access patterns
    description = (
        item.get("description", "")
        if isinstance(item, dict)
        else getattr(item, "description", "")
    )
    desc_lines = description.strip().split("\n")
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

    # Extract item fields with dict/object compatibility
    title = (
        item.get("title", "No title")
        if isinstance(item, dict)
        else getattr(item, "title", "No title")
    )
    price = (
        item.get("price", "N/A")
        if isinstance(item, dict)
        else getattr(item, "price", "N/A")
    )
    location = (
        item.get("location", "N/A")
        if isinstance(item, dict)
        else getattr(item, "location", "N/A")
    )
    created_at = (
        item.get("created_at", "N/A")
        if isinstance(item, dict)
        else getattr(item, "created_at", "N/A")
    )
    item_url = (
        item.get("item_url", "#")
        if isinstance(item, dict)
        else getattr(item, "item_url", "#")
    )
    source = (
        item.get("source") if isinstance(item, dict) else getattr(item, "source", None)
    )

    # Format and escape all user-provided content for MarkdownV2
    title_bold = bold_telegram_md(title)
    price_escaped = _escape_markdown_v2(str(price))
    location_escaped = _escape_markdown_v2(str(location))

    # Format created_at from ISO format to readable format with bold time
    if created_at and created_at != "N/A":
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            date_part = dt.strftime("%d.%m.%Y")
            time_part = dt.strftime("%H:%M")
            # Build the full date string, then escape and bold appropriately
            date_formatted = f"{_escape_markdown_v2(date_part)} {_escape_markdown_v2('-')} {bold_telegram_md(time_part)}"
        except (ValueError, AttributeError):
            date_formatted = _escape_markdown_v2(str(created_at))
    else:
        date_formatted = "N/A"

    text = (
        f"📦 {title_bold}\n\n"
        f"💰 {bold_telegram_md('Price')}: {price_escaped}\n"
        f"📍 {bold_telegram_md('Location')}: {location_escaped}\n"
        f"🕒 {bold_telegram_md('Posted')}: {date_formatted}\n"
    )
    # Optional extras
    if price_info := extra.get("price_info"):
        text += f"💵 {bold_telegram_md('Price')}: {price_info}\n"
    if (deposit := extra.get("deposit_info")) and deposit != "Deposit: 0":
        text += f"🔐 {bold_telegram_md('Deposit')}: {deposit}\n"
    if animals := extra.get("animals_info"):
        text += f"🐾 {bold_telegram_md('Animals')}: {animals}\n"
    if rent := extra.get("rent_info"):
        text += f"💳 {bold_telegram_md('Rent')}: {rent}\n"

    platform_name = _escape_markdown_v2(source if source else "Unknown source")
    item_url_escaped = _escape_markdown_v2(item_url)
    text += f"🔗 [View on {platform_name}]({item_url_escaped})"
    return text
