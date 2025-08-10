import importlib
import os
import sys
import types
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch


class TestConfig(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Provide minimal env for settings
        self.env = {
            "BOT_TOKEN": "token",
            "CHAT_IDS": "123",
            "TOPN_DB_BASE_URL": "http://localhost:8000",
            "CHECK_FREQUENCY_SECONDS": "5",
            "DB_REMOVE_OLD_ITEMS_DATA_N_DAYS": "3",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
        }
        self._old_env = os.environ.copy()
        os.environ.update(self.env)

    async def asyncTearDown(self):
        os.environ.clear()
        os.environ.update(self._old_env)

    async def test_settings_loads_from_env(self):
        from core import config

        importlib.reload(config)
        s = config.settings
        self.assertEqual(s.BOT_TOKEN, self.env["BOT_TOKEN"])
        self.assertEqual(s.CHAT_IDS, self.env["CHAT_IDS"])
        self.assertEqual(s.TOPN_DB_BASE_URL, self.env["TOPN_DB_BASE_URL"])
        self.assertEqual(
            s.CHECK_FREQUENCY_SECONDS, int(self.env["CHECK_FREQUENCY_SECONDS"])
        )
        self.assertEqual(
            s.DB_REMOVE_OLD_ITEMS_DATA_N_DAYS,
            int(self.env["DB_REMOVE_OLD_ITEMS_DATA_N_DAYS"]),
        )
        self.assertEqual(s.REDIS_HOST, self.env["REDIS_HOST"])
        self.assertEqual(s.REDIS_PORT, int(self.env["REDIS_PORT"]))


class TestMain(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Reuse environment from TestConfig assumptions
        self.env = {
            "BOT_TOKEN": "token",
            "CHAT_IDS": "123",
            "TOPN_DB_BASE_URL": "http://localhost:8000",
            "CHECK_FREQUENCY_SECONDS": "5",
            "DB_REMOVE_OLD_ITEMS_DATA_N_DAYS": "3",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
        }
        self._old_env = os.environ.copy()
        os.environ.update(self.env)

    async def asyncTearDown(self):
        os.environ.clear()
        os.environ.update(self._old_env)

    async def test_telegram_main_wires_and_starts(self):
        # Patch heavy deps before importing/reloading main
        with patch("redis.asyncio.Redis", return_value=MagicMock()) as RedisCtor, patch(
            "aiogram.fsm.storage.redis.RedisStorage", return_value=MagicMock()
        ) as StorageCtor, patch("aiogram.Bot") as BotCtor, patch(
            "aiogram.Dispatcher"
        ) as DispatcherCtor:

            # Fake dp with message.register and start_polling
            fake_dp = MagicMock()
            fake_dp.message.register = MagicMock()
            fake_dp.start_polling = AsyncMock(side_effect=RuntimeError("stop"))
            DispatcherCtor.return_value = fake_dp

            # Import and reload main to bind patched constructors
            dummy_monitoring = types.SimpleNamespace(
                cmd_start_monitoring=AsyncMock(),
                process_url=AsyncMock(),
                process_name=AsyncMock(),
                process_status_choice=AsyncMock(),
                process_stop_choice=AsyncMock(),
                stop_monitoring_command=AsyncMock(),
            )
            dummy_keyboards = types.SimpleNamespace(MAIN_MENU_KEYBOARD=MagicMock())
            with patch.dict(
                sys.modules,
                {
                    "bot.handlers.monitoring": dummy_monitoring,
                    "bot.keyboards": dummy_keyboards,
                },
            ):
                import main

                importlib.reload(main)

            # Ensure dp is our fake (safety)
            main.dp = fake_dp

            fake_repo = MagicMock()
            # Use non-async mocks so patched create_task doesn't get coroutines
            fake_repo.remove_old_items_data_infinitely = MagicMock()
            fake_svc = MagicMock()
            notifier_instance = MagicMock()
            notifier_instance.run_periodically = MagicMock()

            with patch.object(
                main, "get_monitoring_service", return_value=fake_svc
            ), patch.object(
                main, "get_repository", return_value=fake_repo
            ), patch.object(
                main, "Notifier", return_value=notifier_instance
            ), patch.object(
                main.asyncio, "create_task", side_effect=lambda _: None
            ):

                bot_instance = BotCtor.return_value
                bot_instance.send_message = AsyncMock()

                # Run and exit via raised RuntimeError from start_polling
                try:
                    await main.telegram_main()
                except RuntimeError:
                    pass

                from core import config

                BotCtor.assert_called_once_with(token=config.settings.BOT_TOKEN)
                self.assertTrue(fake_dp.message.register.called)
                notifier_instance.run_periodically.assert_called_with(
                    config.settings.CHECK_FREQUENCY_SECONDS
                )
                fake_repo.remove_old_items_data_infinitely.assert_called_with(
                    config.settings.DB_REMOVE_OLD_ITEMS_DATA_N_DAYS
                )
                fake_dp.start_polling.assert_awaited()
                bot_instance.send_message.assert_any_await(
                    chat_id=config.settings.CHAT_IDS, text="BOT WAS STARTED"
                )
                bot_instance.send_message.assert_any_await(
                    chat_id=config.settings.CHAT_IDS, text="BOT WAS STOPPED"
                )
