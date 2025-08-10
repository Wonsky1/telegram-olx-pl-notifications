import asyncio
import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from services.notifier import Notifier, _format_item_text


class TestNotifier(IsolatedAsyncioTestCase):
    async def test_format_item_text_variants(self):
        item_dict = {
            "title": "Nice flat",
            "price": "2000",
            "location": "Warsaw",
            "created_at_pretty": "today",
            "item_url": "http://x",
            "description": "price: 2000\ndeposit: 1000\nanimals_allowed: true\nrent: 300",
            "source": "olx",
        }
        text = _format_item_text(item_dict)
        self.assertIn("Nice flat", text)
        self.assertIn("Price:", text)
        self.assertIn("Deposit:", text)
        self.assertIn("Pets: Allowed", text)
        self.assertIn("Additional rent:", text)
        self.assertIn("View on olx", text)

        # Object-like access
        class Obj:
            title = "T"
            price = "P"
            location = "L"
            created_at_pretty = "C"
            item_url = "U"
            description = ""

        text2 = _format_item_text(Obj())
        self.assertIn("T", text2)
        self.assertIn("View on Unknown source", text2)

    async def test_check_and_send_items_none(self):
        bot = AsyncMock()
        svc = AsyncMock()
        svc.pending_tasks.return_value = [MagicMock(chat_id="1", name="n", id=7)]
        svc.items_to_send.return_value = []

        n = Notifier(bot, svc)
        await n._check_and_send_items()

        svc.update_last_updated.assert_awaited()  # called for empty items
        svc.update_last_got_item.assert_not_called()
        bot.send_message.assert_not_awaited()

    async def test_check_and_send_items_with_items(self):
        bot = AsyncMock()
        svc = AsyncMock()
        task = MagicMock(chat_id="1", name="n", id=7)
        items = [
            {
                "title": "A",
                "price": "1",
                "location": "L",
                "created_at_pretty": "C",
                "item_url": "U",
                "image_url": None,
            },
            {
                "title": "B",
                "price": "2",
                "location": "L",
                "created_at_pretty": "C",
                "item_url": "U",
                "image_url": "IMG",
            },
        ]
        svc.pending_tasks.return_value = [task]
        svc.items_to_send.return_value = items

        n = Notifier(bot, svc)
        with patch("asyncio.sleep", new=AsyncMock()) as _:
            await n._check_and_send_items()

        # First a caption photo notification
        bot.send_photo.assert_any_await(
            chat_id="1", photo=unittest.mock.ANY, caption=unittest.mock.ANY
        )
        # Then per-item messages/photos
        bot.send_message.assert_awaited()  # for item without image
        bot.send_photo.assert_awaited()  # for item with image
        svc.update_last_got_item.assert_awaited_with("1")
        svc.update_last_updated.assert_awaited_with(task)

    async def test_run_periodically_breaks(self):
        bot = AsyncMock()
        svc = AsyncMock()
        n = Notifier(bot, svc)

        async def fake_sleep(_):
            raise asyncio.CancelledError

        with patch.object(n, "_check_and_send_items", new=AsyncMock()) as check:
            with patch("services.notifier.asyncio.sleep", new=fake_sleep):
                with self.assertRaises(asyncio.CancelledError):
                    await n.run_periodically(1)
        check.assert_awaited()
