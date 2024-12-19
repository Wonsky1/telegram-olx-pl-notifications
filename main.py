import asyncio
from datetime import datetime, timedelta
import os
from typing import List, Union

from aiogram import Bot, Dispatcher, types
from aiogram.exceptions import TelegramNetworkError, TelegramServerError

from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
from aiogram.utils.chat_action import ChatActionSender

import logging
from db.database import (
    get_db,
    create_task,
    get_task_by_chat_id,
    delete_task_by_chat_id,
    init_db,
    get_users_pending,
)
from tools.app_funcs import get_new_flats
from tools.models import Flat
from tools.utils import get_link
from core.config import settings

# def allowed_gai_family():
#     return socket.AF_INET
#
#
# urllib3_cn.allowed_gai_family = allowed_gai_family
load_dotenv()


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


bot = Bot(token=os.getenv("BOT_TOKEN"))

dp = Dispatcher()
tasks = {}
bot_task = None

init_db()

db = next(get_db())


async def on_startup():
    asyncio.create_task(send_periodic_message())

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


async def send_messages(bot_, chat_id: Union[str, int], url: str):
    async with ChatActionSender.typing(bot=bot_, chat_id=chat_id):
        flats = await get_new_flats(url=url)

        logging.info(f"Sending {len(flats)} flats to {chat_id}")
        await send_flats_message(chat_id, flats)



async def send_periodic_message():
    while True:
        users = get_users_pending(db)
        if not users:
            await asyncio.sleep(60)
            continue

        for chat_id, url in users:
            await send_messages(bot, chat_id, url)

            task = get_task_by_chat_id(db, chat_id)
            if task:
                task.last_updated = datetime.now()
                db.commit()


@dp.message(Command(commands=["start_monitoring"]))
async def start_monitoring(message: Message):
    chat_id = message.chat.id
    url = get_link(message.text)
    task = get_task_by_chat_id(db, str(chat_id))
    if not task:
        create_task(db, chat_id=str(chat_id), url=url if url else settings.URL)

        await message.answer("Starting monitoring")
        await send_messages(bot, message.chat.id, url)
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
    chat_id = settings.CHAT_IDS

    try:
        await bot.send_message(chat_id=chat_id, text="BOT WAS STARTED")
        try:
            dp.startup.register(on_startup)
            await dp.start_polling(bot)

        except TelegramNetworkError as e:
            logging.error(f"Failed to fetch updates - TelegramNetworkError: {e}")
        except TelegramServerError as e:
            logging.error(f"Failed to fetch updates - TelegramServerError: {e}")
            await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

    finally:
        await bot.send_message(chat_id=chat_id, text="BOT WAS STOPPED")
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

