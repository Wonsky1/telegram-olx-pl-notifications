from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from services.validator import UrlValidator


class TestUrlValidator(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.validator = UrlValidator()

    async def asyncTearDown(self):
        pass

    async def test_is_supported(self):
        self.assertTrue(self.validator.is_supported("https://olx.pl/abc"))
        self.assertTrue(self.validator.is_supported("https://www.olx.pl/abc"))
        self.assertTrue(self.validator.is_supported("https://m.olx.pl/abc"))
        self.assertFalse(self.validator.is_supported("https://example.com"))

    async def test_normalize_variants(self):
        self.assertEqual(
            self.validator.normalize("https://olx.pl/abc?b=2&a=1"),
            "https://www.olx.pl/abc?a=1&b=2",
        )
        self.assertEqual(
            self.validator.normalize("https://m.olx.pl/path/"),
            "https://www.olx.pl/path/",
        )
        self.assertEqual(
            self.validator.normalize("https://www.m.olx.pl/path/"),
            "https://www.olx.pl/path/",
        )

    @patch("services.validator.is_valid_and_accessible", new_callable=AsyncMock)
    async def test_is_reachable_true(self, mock_check):
        mock_check.return_value = True
        self.assertTrue(await self.validator.is_reachable("https://www.olx.pl/x"))

    @patch("services.validator.is_valid_and_accessible", new_callable=AsyncMock)
    async def test_is_reachable_false(self, mock_check):
        mock_check.return_value = False
        self.assertFalse(await self.validator.is_reachable("https://www.olx.pl/x"))
