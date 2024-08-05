import asyncio
from datetime import datetime, timedelta
import os
from typing import List, Union

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup


load_dotenv()

bot = Bot(os.getenv("BOT_TOKEN"))
dp = Dispatcher()

tasks = {}


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
        for flat in flats:
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
    # await bot.send_message(chat_id, "ИХИХХИХИХ БРОКОЛІІІІІ", parse_mode=ParseMode.MARKDOWN)
    while True:
        flats = await get_new_flats()
        print(f"Sending {len(flats)} flats to {chat_id}")
        await send_flats_message(chat_id, flats)
        # await bot.send
        await asyncio.sleep(3600)


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

    six_minutes_ago = (datetime.combine(now.date(), current_time) - timedelta(minutes=90)).time()

    return time_provided >= six_minutes_ago

async def get_new_flats() -> Union[List[Flat], None]:
    print(f"Getting new flats at {datetime.now().strftime('%H:%M')}")
    result = []
    url = os.getenv("URL", "https://www.olx.pl/nieruchomosci/mieszkania/wynajem/warszawa/?search%5Bprivate_business%5D=private&search%5Border%5D=created_at:desc&search%5Bfilter_float_price:to%5D=2500&search%5Bfilter_enum_rooms%5D%5B0%5D=one")
    headers = {
        # ":authority": "www.olx.pl",
        # ":method": "GET",
        # ":path": "/nieruchomosci/mieszkania/wynajem/warszawa/?search%5Bfilter_enum_rooms%5D%5B0%5D=two&search%5Border%5D=created_at%3Adesc&search%5Bprivate_business%5D=private",
        # ":scheme": "https",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "max-age=0",
        # "Cookie": "deviceGUID=69fe2197-5b13-4523-ace7-5fb6d43c2beb; a_refresh_token=37f2b28c1c4e17ee59dd703e37279260b1aad0bc; a_grant_type=device; __user_id_P&S=2317556410; observed_aui=63db584d72b54d2e9943e7c210bdebe4; OptanonAlertBoxClosed=2024-07-01T10:37:55.630Z; eupubconsent-v2=CQBElXAQBElXAAcABBENA7E8AP_gAAAAAAYgKENV_G_fbXlj8X50aftkeY1f99h7rsQxBhfJk-4FyLuW_JwX32EzNA16pqYKmRIEu3bBIQFlHIDUDUCgaogVrTDMakWMgTNKJ6BEiFMRe2dYCF5vmwFD-QKY5tpt93d52Re9_dv83dzyz4Vnn3Kp_2e1WJCdA5cgAAAAAAAAAAAAAAAQAAAAAAAAAQAIAAAAAAAAAAAAAAAAAAAAF_cAAAALlAAAAUEggAAIAAXABQAFQAOAAeABBAC8ANQAeABEACYAFUAN4AegA_ACEgEMARIAjgBLACaAGAAMOAZQBlgDZAHPAO4A74B7AHxAPsA_YB_gIAARSAi4CMAEaAJLAT8BQYCoAKuAXMAvQBigDRAG0ANwAcSBHoEiAJ2AUOAo8BSIC2AFyALvAXmAwYBhsDIwMkAZOAy4BmYDOYGrgayA2MBt4DdQHBAOTAcuEALAAOABIAEcAg4BHACaAF9ASsAm0BSACuQFhALEAXkAxABiwDIQGjANTAbQA24Bug4BSAAiABwAHgAXABIAD8AI4AaABHADkAIBAQcBCACIgEcAJoAVAA6QCEAErAJiATKAm0BScCuQK7AWIAtQBdADBAGIAMWAZCAyYBowDUwGvANoAbYA24BugDjwHLQOdA58dBKAAXABQAFQAOAAggBcAGoAPAAiABMACrAFwAXQAxABvAD0AH6AQwBEgCWAE0AKMAYAAwwBlADRAGyAOeAdwB3gD2gH2AfoA_4CKAIxAR0BJYCfgKDAVEBVwCxAFzgLyAvQBigDaAG4AOIAdQA-wCL4EegSIAmQBOwCh4FHgUgApoBVgCxQFsALdAXAAuQBdoC7wF5gL6AYMAw0Bj0DIwMkAZOAyqBlgGXAMzAZyA02Bq4GsANvAbqA4sByYDlyABUABAADwA0ADkAI4AWIAvoCbQFJgK5AWIAvIBggDPAGjANTAbYA24BugDlgHPkIEIACwAKAAuABqAEwAKoAXAAxABvAD0AI4AYAA54B3AHeAP8AigBKQCgwFRAVcAuYBigDaAHUAR6ApoBVgCxQFogLgAXIAyMBk4DOSUCEABAACwAKAAcAB4AEQAJgAVQAuABigEMARIAjgBRgDAAGyAO8AfkBUQFXALmAYoA6gCJgEXwI9AkQBR4CxQFsALzgZGBkgDJwGcgNYAbeSAIgAXACOAO4AgABBwCOAFQASsAmIBNoCkwGLAMsAZ4A3IBugDlikDkABcAFAAVAA4ACCAGgAagA8ACIAEwAKoAYgA_QCGAIkAUYAwABlADRAGyAOcAd8A_AD9AIsARiAjoCSgFBgKiAq4BcwC8gGKANoAbgA6gB7QD7AImARfAj0CRAE7AKHAUgAqwBYoC2AFwALkAXaAvMBfQDDYGRgZIAyeBlgGXAM5gawBrIDbwG6gOCAcmUAPgAXABIAC4AGQARwBHADkAHcAPsAgABBwCxAF1ANeAdsA_4CYgE2gKkAV2AugBeQDBAGLAMmAZ4A0YBqYDXgG6AOWAA.f_wAAAAAAAAA; OTAdditionalConsentString=1~89.320.1421.1423.1659.1985.2008.2072.2135.2322.2465.2501.2958.2999.3028.3225.3226.3231.3234.3235.3236.3237.3238.3240.3244.3245.3250.3251.3253.3257.3260.3270.3272.3281.3288.3290.3292.3293.3296.3299.3300.3306.3307.3309.3314.3315.3316.3318.3324.3328.3330.3331.3531.3731.3831.3931.4131.4531.4631.4731.4831.5231.6931.7235.7831.7931.8931.9731.10231.10631.10831.11031.11531.12831.13632.13731.14237.14332.15731.16831.16931.21233.23031.24431.25731.25931.26031.26831.27731.27831.28031.28731.28831.29631.31631; __gsas=ID=df574f97e00b9da1:T=1719830276:RT=1719830276:S=ALNI_MY5Albt6GPAoKMoIMr2xHXHRYRkBw; laquesissu=295@listing|1#298@reply_chat_sent|1; _gcl_au=1.1.684374207.1719830276; __rtbh.lid=%7B%22eventType%22%3A%22lid%22%2C%22id%22%3A%22oiA9YMt5wbbfULD61TfU%22%7D; __rtbh.uid=%7B%22eventType%22%3A%22uid%22%7D; session_start_date=1721143720275; OptanonConsent=isGpcEnabled=0&datestamp=Tue+Jul+16+2024+16%3A58%3A40+GMT%2B0200+(Central+European+Summer+Time)&version=202402.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&genVendors=V10%3A0%2C&consentId=4fbef97d-577f-4469-9bec-40c4fe2f424f&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1%2Cgad%3A1&geolocation=PL%3B14&AwaitingReconsent=false; PHPSESSID=ca7fogrin08mps6b8g2ojhsoke; a_access_token=fd08f9baf4e4708b80e16c5b47832780ba858154; _hjSessionUser_1685071=eyJpZCI6ImMwYjUwNGVlLTE2NjAtNWMwNS04NzYzLTkwYjMxNzI4OWI2ZCIsImNyZWF0ZWQiOjE3MTk4MzAyNzU4OTAsImV4aXN0aW5nIjp0cnVlfQ==; _hjSession_1685071=eyJpZCI6ImRiMmE1ZDkwLTI4M2EtNGNiYy1hNjAwLWFhM2JiZTE2YWMzZCIsImMiOjE3MjExNDE5MjA3NjIsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowLCJzcCI6MH0=; __gfp_64b=xC8r_y1hwsXLEOFQa8xYcBULGlM3Sq1_zziOrXhJIdj..7|1719830275|2; _cc_id=5e9bb502f4d3481d7411498a38355bda; panoramaId_expiry=1721746720972; panoramaId=8165ffeddf9d109c4bf77b906570c8bd038a65c4cfd8773658cadf7d5100d3b7; panoramaIdType=panoIndiv; user_id=2317556410; user_uuid=; user_business_status=private; cto_bundle=6UiOgl83NFR4a2VQc3R6OTc1QiUyRjJjanpTY05hUHNYMDZKenczVHowZ0pFV0ZiMmNOU3NGc2h1d0VQQ1BrM1dPNWt4NGljWnZ1U3pqUmY3c3lCN2g3R3NuWldRTmxLU0wwQVNMakFMaEplZmIlMkZOdzBJMjdlaXFHeXpHcmZuR3ZkbiUyQk41aWx4dFZ5RjVwV25RTHZQJTJCb2IyYTZSZFFmbU9NZHp1dkJubzVYYXNSRm40Z2FDS0N4RlZnc3AyVnhFNHhpVDZjTg; _gid=GA1.2.1122845970.1721141921; laquesis=aut-2972@b#cou-1752@b#dc-18@b#erm-1545@a#erm-1575@a#erm-1623@a#jobs-7019@a#jobs-7031@a#jobs-7269@b#jobs-7504@b#jobs-7508@b#jobs-7735@b#olxeu-41791@b#olxeu-41847@a#olxeu-41855@b#olxeu-41938@b#olxeu-41974@a#tsm-208@c; laquesisff=a2b-000#aut-1425#aut-388#bl-2928#buy-2279#buy-2489#buy-4410#cou-1670#dat-2874#de-1514#de-1927#de-1928#de-2559#de-2724#decision-256#do-2963#do-3418#euit-2250#euonb-114#f8nrp-1779#grw-124#jobs-7611#kuna-307#kuna-554#kuna-603#mart-1341#mou-1052#oesx-1437#oesx-2063#oesx-2798#oesx-2864#oesx-2926#oesx-3069#oesx-3150#oesx-3713#oesx-645#oesx-867#olxeu-0000#psm-308#psm-402#psm-457#psm-574#rm-28#rm-59#rm-707#rm-824#sd-2240#sd-2759#sd-570#srt-1289#srt-1346#srt-1434#srt-1593#srt-1758#srt-683#uacc-529#uacc-561#up-90; lqstatus=1721143181|190bc0d85cbx75724d68|jobs-7735|||0; ab.storage.sessionId.535b859e-9238-4873-a90e-4c76b15ce078=%7B%22g%22%3A%2221a7ae29-b913-4168-4871-f1a1c63c186e%22%2C%22e%22%3A1721143721406%2C%22c%22%3A1721141921406%2C%22l%22%3A1721141921406%7D; ab.storage.deviceId.535b859e-9238-4873-a90e-4c76b15ce078=%7B%22g%22%3A%226090146b-6a0b-218e-510a-6eb7530760d0%22%2C%22c%22%3A1719830286004%2C%22l%22%3A1721141921406%7D; _ga_6PZTQNYS5C=GS1.1.1721141921.2.0.1721141921.60.0.0; _ga=GA1.1.326829121.1719830276; _ga_1MNBX75RRH=GS1.1.1721141921.2.0.1721141921.0.0.0; __gads=ID=31a9c81e9ba1bfdb:T=1719830276:RT=1721141921:S=ALNI_Ma1MGw7OR5bJpvFTKQ7pxeFhnj3Hw; __gpi=UID=00000e6ce592c107:T=1719830276:RT=1721141921:S=ALNI_MawENNHXwLTYjwwaQVczlm2EFVPRw; __eoi=ID=1b57948f59961c54:T=1719830276:RT=1721141921:S=AA-AfjZ4L4U2r-u65x4wpgwS8jRR; _ga_V1KE40XCLR=GS1.1.1721141921.2.0.1721141922.59.0.0; WPabs=61e2ed; onap=1906ddf6745x206e35b-2-190bc0d85cbx75724d68-14-1721143728",
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
    # location, date = location_date.get_text(strip=True))
    print(f"Found {len(result)} flats")
    return result

async def main() -> None:
    # chat_ids = input("Please, wr")
    try:
        await dp.start_polling(bot)
    finally:
        # for chat_id in list(os.getenv("CHAT_IDS")):
        await bot.send_message(chat_id=os.getenv("CHAT_IDS"), text="BOT WAS STOPPED")
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())