import asyncio
import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from services.notifier import Notifier, _escape_markdown, _format_item_text


class TestEscapeMarkdown(unittest.TestCase):
    """Test the _escape_markdown helper function."""

    def test_escape_special_characters(self):
        """Test that all special Markdown characters are escaped."""
        input_text = "Test *bold* _italic_ [link](url) `code` ~strike~"
        result = _escape_markdown(input_text)
        self.assertIn(r"\*bold\*", result)
        self.assertIn(r"\_italic\_", result)
        self.assertIn(r"\[link\]\(url\)", result)
        self.assertIn(r"\`code\`", result)
        self.assertIn(r"\~strike\~", result)

    def test_escape_all_special_chars(self):
        """Test escaping of all special characters."""
        special = "_*[]()~`>#+-=|{}.!"
        result = _escape_markdown(special)
        # Each character should be prefixed with a backslash
        for char in special:
            self.assertIn(f"\\{char}", result)

    def test_escape_empty_string(self):
        """Test that empty string is handled correctly."""
        result = _escape_markdown("")
        self.assertEqual(result, "")

    def test_escape_none(self):
        """Test that None is handled correctly."""
        result = _escape_markdown(None)
        self.assertIsNone(result)

    def test_escape_regular_text(self):
        """Test that regular text without special chars is unchanged."""
        text = "This is normal text"
        result = _escape_markdown(text)
        self.assertEqual(result, text)

    def test_escape_real_world_title(self):
        """Test escaping a real-world title with special characters."""
        title = "2-room flat (50m²) - Modern & Cozy!"
        result = _escape_markdown(title)
        # Should escape parentheses, hyphen, and exclamation
        self.assertIn(r"\(", result)
        self.assertIn(r"\)", result)
        self.assertIn(r"\-", result)
        self.assertIn("&", result)  # & doesn't need escaping, should remain
        self.assertIn(r"\!", result)

    def test_escape_price_with_currency(self):
        """Test escaping prices with special formatting."""
        price = "1,500-2,000 PLN"
        result = _escape_markdown(price)
        # Hyphen should be escaped, comma doesn't need escaping
        self.assertIn(r"\-", result)
        self.assertIn(",", result)  # Comma should remain unescaped


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

    async def test_format_item_text_with_special_characters(self):
        """Test that special Markdown characters in item data are properly escaped."""
        item_dict = {
            "title": "2-room flat (50m²) - *New* & Cozy!",
            "price": "1,500-2,000",
            "location": "Warsaw [Center]",
            "created_at_pretty": "today (2h ago)",
            "item_url": "http://example.com",
            "description": "price: 1,800\ndeposit: 500",
            "source": "OLX.pl",
        }
        text = _format_item_text(item_dict)
        # Should contain escaped special characters
        self.assertIn(r"\(", text)
        self.assertIn(r"\)", text)
        self.assertIn(r"\*", text)
        self.assertIn(r"\[", text)
        self.assertIn(r"\]", text)
        self.assertIn(r"\-", text)
        self.assertIn(r"\!", text)
        self.assertIn(r"\.", text)
        # Should not break the Markdown structure
        self.assertIn("📦 *", text)  # Emoji and bold marker for title
        self.assertIn("💰 *Price:*", text)  # Bold markers for labels

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
