import asyncio
from datetime import datetime, timedelta
import os
from typing import List, Union
import validators

from aiogram import Bot, Dispatcher, types
from aiogram.exceptions import TelegramNetworkError, TelegramServerError
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import socket
import requests.packages.urllib3.util.connection as urllib3_cn
import logging
from database import get_db, create_task, get_task_by_chat_id, delete_task_by_chat_id, get_all_tasks, init_db


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        tasks[chat_id] = asyncio.create_task(send_periodic_message(chat_id=chat_id, url=url, start_time=last_updated + timedelta(hours=1)))
        logging.info(f"Recreated monitoring task for chat_id {chat_id}")


def allowed_gai_family():
    return socket.AF_INET


urllib3_cn.allowed_gai_family = allowed_gai_family


load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))

dp = Dispatcher()

tasks = {}

LAST_MINUTES_GETTING = 75
SLEEP_MINUTES = 60
URL = os.getenv(
    "URL",
    "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/warszawa/?search%5Bprivate_business%5D=private&search%5Border%5D=created_at:desc&search%5Bfilter_float_price:to%5D=2500&search%5Bfilter_enum_rooms%5D%5B0%5D=one"
)


class Flat:
    def __init__(self, title, price, image_url, created_at, location, flat_url):
        self.title = title
        self.price = price
        self.image_url = image_url
        self.created_at = created_at
        self.location = location
        self.flat_url = flat_url


def get_link(text: str) -> str or None:
    try:
        link = text.split(" ")[1]
        return link
    except Exception:
        return None

async def send_flats_message(chat_id: Union[int,str], flats: List[Flat]):
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
                    chat_id=chat_id,
                    photo=flat.image_url,
                    caption=text
                )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text
                )

async def send_periodic_message(chat_id: int, url: str, start_time: datetime = None):
        while True:
            if start_time is None or start_time <= datetime.now():
                flats = await get_new_flats(url=url)
                logging.info(f"Sending {len(flats)} flats to {chat_id}")
                await send_flats_message(chat_id, flats)
                await asyncio.sleep(SLEEP_MINUTES * 60)
            else:
                await asyncio.sleep(60)


@dp.message(Command(commands=['start_monitoring']))
async def start_monitoring(message: Message):

    chat_id = message.chat.id
    url = get_link(message.text)
    task = get_task_by_chat_id(db, str(chat_id))
    if not task:
        create_task(db, chat_id=str(chat_id), url=url if url else URL)

        tasks[chat_id] = asyncio.create_task(send_periodic_message(chat_id=chat_id, url=url if url else URL))
        await message.answer("Starting monitoring")
    else:
        await message.answer("Monitoring is already started")

@dp.message(lambda message: message.text and message.text.lower() == '/end_monitoring')
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


def is_time_within_last_6_minutes(time_str: str) -> bool:
    time_format = '%H:%M'
    try:
        time_provided = datetime.strptime(time_str, time_format).time()
    except ValueError:
        logging.error(f"Invalid time format: {time_str}")
        return False

    now = datetime.now() - timedelta(hours=2)
    current_time = now.time()

    six_minutes_ago = (datetime.combine(now.date(), current_time) - timedelta(minutes=LAST_MINUTES_GETTING)).time()

    return time_provided >= six_minutes_ago


def is_valid_and_accessible(url: str) -> bool:
    """Check if a URL is valid and returns a successful response."""
    if not validators.url(url):
        return False

    try:
        response = requests.get(url)
        return response.status_code == 200
    except requests.RequestException:
        return False


def get_valid_url(url: str, fallback_url: str) -> str:
    """Return the provided URL if valid and accessible, otherwise return the fallback URL."""
    return url if is_valid_and_accessible(url) else fallback_url


async def get_new_flats(
    url: str = URL
) -> Union[List[Flat], None]:
    url = get_valid_url(url, URL)
    logging.info(f"Getting new flats at {datetime.now().strftime('%H:%M')}")
    result = []
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "max-age=0",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    logging.info(response.status_code)
    soup = BeautifulSoup(response.text, 'html.parser')
    divs = soup.find_all('div', attrs={'data-testid': "l-card"})
    for div in divs:
        location_date = div.find('p', attrs={'data-testid': 'location-date'}).get_text(strip=True)

        if not "Dzisiaj" in location_date:
            continue

        location, time = location_date.split("Dzisiaj o ")
        location = location.strip()
        if location.endswith("-"):
            location = location[:-1]
        is_within = is_time_within_last_6_minutes(time)
        if is_within:
            continue

        image_url = None
        img_tag = div.find('img')
        if img_tag and img_tag.has_attr('src'):
            image_url = img_tag['src']

        price_tag = div.find('p', attrs={'data-testid': 'ad-price'})
        price = price_tag.get_text(strip=True)

        title = div.find('div', attrs={'data-cy': 'ad-card-title'})
        a_tag = title.find('a')

        # Get the href attribute from the <a> tag
        flat_url = a_tag['href']
        flat_url = "https://www.olx.pl" + flat_url
        title = title.get_text(strip=True)

        time_provided = datetime.strptime(time, "%H:%M").time()
        date_placeholder = datetime(2000, 1, 1)  # Date doesn't matter here
        datetime_provided = datetime.combine(date_placeholder, time_provided)
        datetime_provided += timedelta(hours=2)
        time = datetime_provided.time().strftime('%H:%M')


        result.append(Flat(
            title=title,
            price=price,
            location=location,
            created_at=time,
            image_url=image_url,
            flat_url=flat_url
        ))
    logging.info(f"Found {len(result)} flats")
    return result


async def main() -> None:
    chat_id = os.getenv("CHAT_IDS")
    await recreate_tasks()
    try:
        await bot.send_message(chat_id=chat_id, text="BOT WAS STARTED")
        while True:
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
