import asyncio
import logging
from datetime import datetime, timedelta
from typing import Union, List

from core.config import settings
from tools.models import Flat
from tools.utils import get_valid_url, is_time_within_last_n_minutes
import requests
from bs4 import BeautifulSoup
import socket
# import requests.packages.urllib3.util.connection as urllib3_cn


async def get_new_flats(
    url: str = settings.URL
) -> List[Flat]:
    url = get_valid_url(url, settings.URL)
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
        is_within = is_time_within_last_n_minutes(time)
        if not is_within:
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
        datetime_provided += timedelta(hours=1)
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

