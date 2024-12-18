import asyncio
from datetime import datetime, timedelta
import os
from typing import List, Union


from aiogram import Bot, Dispatcher, types
from aiogram.exceptions import TelegramNetworkError, TelegramServerError
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import socket

# import requests.packages.urllib3.util.connection as urllib3_cn
import logging
from db.database import (
    get_db,
    create_task,
    get_task_by_chat_id,
    delete_task_by_chat_id,
    get_all_tasks,
    init_db,
)
from tools.app_funcs import get_new_flats
from tools.models import Flat
from tools.utils import get_link, get_valid_url
from core.config import settings

# def allowed_gai_family():
#     return socket.AF_INET
#
#
# urllib3_cn.allowed_gai_family = allowed_gai_family

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

tasks = {}

init_db()

db = next(get_db())


async def recreate_tasks():
    """Recreate monitoring tasks from the database after bot restart."""
    tasks_from_db = get_all_tasks(db)

    for task in tasks_from_db:
        chat_id = int(task.chat_id)
        url = task.url
        last_updated = task.last_updated

        # Recreate the asyncio task
        tasks[chat_id] = asyncio.create_task(
            send_periodic_message(
                chat_id=chat_id, url=url, start_time=last_updated + timedelta(hours=1)
            )
        )
        logging.info(f"Recreated monitoring task for chat_id {chat_id}")


async def send_flats_message(chat_id: Union[int, str], flats: List[Flat]):
    if flats:
        await bot.send_photo(
            chat_id=chat_id,
            photo="https://tse4.mm.bing.net/th?id=OIG2.fso8nlFWoq9hafRkva2e&pid=ImgGn",
            caption=f"I have found {len(flats)} flats, maybe one of them is going to be mouses new flat",
        )
        for flat in flats[::-1]:
            text = (
                f"{flat.title}\n"
                f"price: {flat.price}\n"
                f"location: {flat.location}\n"
                f"created_at: {flat.created_at}\n"
                f"flat_url: {flat.flat_url}"
            )
            if not flat.image_url.startswith("http"):
                flat.image_url = None
            if flat.image_url:
                await bot.send_photo(
                    chat_id=chat_id, photo=flat.image_url, caption=text
                )
            else:
                await bot.send_message(chat_id=chat_id, text=text)


async def send_periodic_message(chat_id: int, url: str, start_time: datetime = None):
    while True:
        if start_time is None or start_time <= datetime.now():
            flats = await get_new_flats(url=url)
            logging.info(f"Sending {len(flats)} flats to {chat_id}")
            await send_flats_message(chat_id, flats)
            await asyncio.sleep(settings.SLEEP_MINUTES * 60)
        else:
            await asyncio.sleep(60)


@dp.message(Command(commands=["start_monitoring"]))
async def start_monitoring(message: Message):

    chat_id = message.chat.id
    url = get_link(message.text)
    task = get_task_by_chat_id(db, str(chat_id))
    if not task:
        create_task(db, chat_id=str(chat_id), url=url if url else settings.URL)

        tasks[chat_id] = asyncio.create_task(
            send_periodic_message(chat_id=chat_id, url=url if url else settings.URL)
        )
        await message.answer("Starting monitoring")
    else:
        await message.answer("Monitoring is already started")


@dp.message(lambda message: message.text and message.text.lower() == "/end_monitoring")
async def end_monitoring(message: Message):
    chat_id = str(message.chat.id)
    task = get_task_by_chat_id(db, chat_id)
    if task:
        delete_task_by_chat_id(db, chat_id)
        if chat_id in tasks:
            tasks[chat_id].cancel()
            del tasks[chat_id]
        await message.answer("Monitoring stopped")
    else:
        await message.answer("Monitoring is already stopped")


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    kb = [
        [
            types.KeyboardButton(text="/start_monitoring"),
            types.KeyboardButton(text="/end_monitoring"),
        ],
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Start or stop monitoring",
    )
    await message.answer("Hello Yana, this is a bot for you <3", reply_markup=keyboard)


async def main() -> None:
    chat_id = os.getenv("CHAT_IDS")
    await recreate_tasks()
    try:
        await bot.send_message(chat_id=chat_id, text="BOT WAS STARTED")
        # while True:
        try:
            await dp.start_polling(bot)

        except TelegramNetworkError as e:
            logging.error(f"Failed to fetch updates - TelegramNetworkError: {e}")
            await asyncio.sleep(1)  # Sleep before retrying
        except TelegramServerError as e:
            logging.error(f"Failed to fetch updates - TelegramServerError: {e}")
            await asyncio.sleep(1)  # Sleep before retrying
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            await asyncio.sleep(1)  # Sleep before retrying

    finally:
        await bot.send_message(chat_id=chat_id, text="BOT WAS STOPPED")
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
