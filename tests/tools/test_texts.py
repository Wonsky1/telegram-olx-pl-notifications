from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from tools import texts


class TestTexts(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        pass

    async def asyncTearDown(self):
        pass

    @patch("tools.texts.httpx.AsyncClient")
    async def test_is_valid_and_accessible_true(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = lambda: None  # Use lambda instead of AsyncMock
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        ok = await texts.is_valid_and_accessible("http://x")
        self.assertTrue(ok)

    @patch("tools.texts.httpx.AsyncClient")
    async def test_is_valid_and_accessible_false(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("err")
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        ok = await texts.is_valid_and_accessible("http://x")
        self.assertFalse(ok)

    def test_get_link(self):
        self.assertEqual(texts.get_link("cmd http://x"), "http://x")
        self.assertIsNone(texts.get_link("cmd"))

    @patch("tools.texts.is_valid_and_accessible", new_callable=AsyncMock)
    async def test_get_valid_url(self, mock_check):
        self.assertEqual(await texts.get_valid_url("", "fb"), "fb")
        mock_check.return_value = True
        self.assertEqual(await texts.get_valid_url("u", "fb"), "u")
        mock_check.return_value = False
        self.assertEqual(await texts.get_valid_url("u", "fb"), "fb")
