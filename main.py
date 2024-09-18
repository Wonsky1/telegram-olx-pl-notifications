import asyncio
from datetime import datetime, timedelta
import os
from typing import List, Union

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import socket
import requests.packages.urllib3.util.connection as urllib3_cn


def allowed_gai_family():
    return socket.AF_INET


urllib3_cn.allowed_gai_family = allowed_gai_family


load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))

dp = Dispatcher()

tasks = {}

LAST_MINUTES_GETTING = 75
SLEEP_MINUTES = 60


class Flat:
    def __init__(self, title, price, image_url, created_at, location, flat_url):
        self.title = title
        self.price = price
        self.image_url = image_url
        self.created_at = created_at
        self.location = location
        self.flat_url = flat_url


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

async def send_periodic_message(chat_id: int):
    while True:
        flats = await get_new_flats()
        print(f"Sending {len(flats)} flats to {chat_id}")
        await send_flats_message(chat_id, flats)
        # await bot.send
        await asyncio.sleep(SLEEP_MINUTES * 60)


@dp.message(Command(commands=['start_monitoring']))
async def start_monitoring(message: Message):
    chat_id = message.chat.id
    if chat_id not in tasks:
        tasks[chat_id] = asyncio.create_task(send_periodic_message(chat_id))
        await message.answer("Starting monitoring")
    else:
        await message.answer("Monitoring is already started")

@dp.message(lambda message: message.text and message.text.lower() == '/end_monitoring')
async def end_monitoring(message: Message):
    chat_id = message.chat.id
    if chat_id in tasks:
        tasks[chat_id].cancel()
        del tasks[chat_id]
        await message.answer("Monitoring stopped")
    else:
        await message.answer("Monitoring is already stopped")

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Hello Yana, this is a bot for you <3")


def is_time_within_last_6_minutes(time_str: str) -> bool:
    time_format = '%H:%M'
    try:
        time_provided = datetime.strptime(time_str, time_format).time()
    except ValueError:
        print(f"Invalid time format: {time_str}")
        return False

    now = datetime.now() - timedelta(hours=2)
    current_time = now.time()

    six_minutes_ago = (datetime.combine(now.date(), current_time) - timedelta(minutes=LAST_MINUTES_GETTING)).time()

    return time_provided >= six_minutes_ago

async def get_new_flats() -> Union[List[Flat], None]:
    print(f"Getting new flats at {datetime.now().strftime('%H:%M')}")
    result = []
    url = os.getenv("URL", "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/warszawa/?search%5Bprivate_business%5D=private&search%5Border%5D=created_at:desc&search%5Bfilter_float_price:to%5D=2500&search%5Bfilter_enum_rooms%5D%5B0%5D=one")
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "max-age=0",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    print(response.status_code)
    soup = BeautifulSoup(response.text, 'html.parser')
    # with open("index.html", 'w', encoding='utf-8') as file:
    #     file.write(soup.prettify())
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
        if not is_time_within_last_6_minutes(time):
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

        # flat_url = div.find('div', attrs={'data-cy': 'ad-card-url'})
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
    print(f"Found {len(result)} flats")
    return result

async def main() -> None:
    try:
        await bot.send_message(chat_id=os.getenv("CHAT_IDS"), text="BOT WAS STARTED")
        await dp.start_polling(bot)
    finally:
        await bot.send_message(chat_id=os.getenv("CHAT_IDS"), text="BOT WAS STOPPED")
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())