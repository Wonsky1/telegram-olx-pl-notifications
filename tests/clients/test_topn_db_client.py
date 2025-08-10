import os
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from clients.topn_db_client import TopnDbClient


class TestTopnDbClient(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        os.environ.setdefault("TOPN_DB_BASE_URL", "http://localhost:8000")
        self.httpx_client = AsyncMock(spec=httpx.AsyncClient)
        self.client = TopnDbClient("http://api", client=self.httpx_client)

    async def asyncTearDown(self):
        pass

    async def test_make_request_success_json(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"ok": True}
        resp.raise_for_status.return_value = None
        self.httpx_client.request.return_value = resp

        data = await self.client._make_request("GET", "/ping")
        self.assertEqual(data, {"ok": True})
        self.httpx_client.request.assert_awaited_once()

    async def test_make_request_204(self):
        resp = MagicMock()
        resp.status_code = 204
        resp.json.side_effect = AssertionError("json not called for 204")
        resp.raise_for_status.return_value = None
        self.httpx_client.request.return_value = resp

        data = await self.client._make_request("DELETE", "/res")
        self.assertEqual(data, {"success": True})

    async def test_make_request_http_error(self):
        # Simulate HTTP error from httpx
        response = MagicMock()
        response.status_code = 404
        response.text = "not found"
        exc = httpx.HTTPStatusError("err", request=MagicMock(), response=response)

        async def raise_exc(**kwargs):
            raise exc

        self.httpx_client.request.side_effect = raise_exc
        with self.assertRaises(httpx.HTTPStatusError):
            await self.client._make_request("GET", "/bad")

    async def test_endpoint_wrappers_delegate(self):
        with patch.object(self.client, "_make_request", new_callable=AsyncMock) as mr:
            await self.client.get_all_tasks()
            mr.assert_awaited_with("GET", "/api/v1/tasks/")
            await self.client.create_task({"a": 1})
            mr.assert_awaited_with("POST", "/api/v1/tasks/", json_data={"a": 1})
            await self.client.update_task(5, {"b": 2})
            mr.assert_awaited_with("PUT", "/api/v1/tasks/5", json_data={"b": 2})
            await self.client.delete_task_by_id(9)
            mr.assert_awaited_with("DELETE", "/api/v1/tasks/9")
            await self.client.get_items_to_send_for_task(3)
            mr.assert_awaited_with("GET", "/api/v1/tasks/3/items-to-send")
            await self.client.get_items_by_source_url("u", limit=7)
            mr.assert_awaited_with(
                "GET", "/api/v1/items/by-source", params={"source_url": "u", "limit": 7}
            )
            await self.client.delete_old_items(30)
            mr.assert_awaited_with("DELETE", "/api/v1/items/cleanup/older-than/30")


class TestTopnDbClientMore(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.httpx_client = AsyncMock(spec=httpx.AsyncClient)
        self.client = TopnDbClient("http://api", client=self.httpx_client)

    async def test_make_request_generic_exception(self):
        self.httpx_client.request.side_effect = ValueError("boom")
        with self.assertRaises(ValueError):
            await self.client._make_request("GET", "/x")

    async def test_context_manager_closes_own_client(self):
        fake_client = AsyncMock()

        # httpx.AsyncClient() should be constructed and then closed on exit
        with patch(
            "clients.topn_db_client.httpx.AsyncClient", return_value=fake_client
        ):
            async with TopnDbClient("http://api") as c:
                self.assertIsInstance(c, TopnDbClient)
            fake_client.aclose.assert_awaited_once()

    async def test_endpoint_wrappers_all(self):
        c = self.client
        with patch.object(c, "_make_request", new_callable=AsyncMock) as mr:
            await c.get_api_root()
            mr.assert_awaited_with("GET", "/")
            await c.health_check()
            mr.assert_awaited_with("GET", "/health")
            await c.get_tasks_by_chat_id("42")
            mr.assert_awaited_with("GET", f"/api/v1/tasks/chat/42")
            await c.get_task_by_id(7)
            mr.assert_awaited_with("GET", f"/api/v1/tasks/7")
            await c.delete_tasks_by_chat_id("42")
            mr.assert_awaited_with("DELETE", f"/api/v1/tasks/chat/42", params=None)
            await c.delete_tasks_by_chat_id("42", name="m")
            mr.assert_awaited_with(
                "DELETE", f"/api/v1/tasks/chat/42", params={"name": "m"}
            )
            await c.get_pending_tasks()
            mr.assert_awaited_with("GET", "/api/v1/tasks/pending")
            await c.update_last_got_item_timestamp(3)
            mr.assert_awaited_with("POST", f"/api/v1/tasks/3/update-last-got-item")
            await c.get_all_items()
            mr.assert_awaited_with(
                "GET", "/api/v1/items/", params={"skip": 0, "limit": 100}
            )
            await c.get_all_items(skip=10, limit=5)
            mr.assert_awaited_with(
                "GET", "/api/v1/items/", params={"skip": 10, "limit": 5}
            )
            await c.get_recent_items(hours=12, limit=2)
            mr.assert_awaited_with(
                "GET", "/api/v1/items/recent", params={"hours": 12, "limit": 2}
            )
            await c.get_item_by_id(8)
            mr.assert_awaited_with("GET", f"/api/v1/items/8")
            await c.get_item_by_url("U")
            mr.assert_awaited_with("GET", f"/api/v1/items/by-url/U")
            await c.create_item({"a": 1})
            mr.assert_awaited_with("POST", "/api/v1/items/", json_data={"a": 1})
            await c.delete_item_by_id(9)
            mr.assert_awaited_with("DELETE", f"/api/v1/items/9")

    async def test_deprecated_add_item_calls_create_item(self):
        with patch.object(self.client, "create_item", new_callable=AsyncMock) as ci:
            ci.return_value = {"ok": True}
            res = await self.client.add_item({"x": 1})
            self.assertEqual(res, {"ok": True})
            ci.assert_awaited_with({"x": 1})
