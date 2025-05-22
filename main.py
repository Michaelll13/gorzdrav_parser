import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import requests
from bs4 import BeautifulSoup

app = FastAPI()
executor = ThreadPoolExecutor()


class Product(BaseModel):
    name: str
    price: int
    link: str
    image_url: str
    manufacturer: str
    country: str
    substance: str


def parse_products(query: str) -> List[Product]:
    encoded_query = query.replace(" ", "+")
    url = f"https://new.gorzdrav.org/search/?text={encoded_query}"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ru,en;q=0.9",
    }

    cookies = {
        "city": '{"regionId":"MOS"}'
    }

    response = requests.get(url, headers=headers, cookies=cookies)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, "html.parser")
    product_cards = soup.select("div.product-card--desktop")

    results = []

    for card in product_cards:
        try:
            name = card.select_one(".product-card-body__title").get_text(strip=True)
            price_text = card.select_one(".ui-price__price").get_text(strip=True)
            price = int(''.join(filter(str.isdigit, price_text)))
            link = "https://new.gorzdrav.org" + card.select_one("a")["href"]
            image = card.select_one("img")["src"]
            image_url = "https://new.gorzdrav.org" + image

            manufacturer = ""
            country = ""
            substance = ""

            for item in card.select(".product-card__item"):
                label = item.select_one(".product-card__label").get_text(strip=True)
                value = item.select_one(".product-card__value").get_text(strip=True)
                if "Производитель" in label:
                    manufacturer = value.strip(", ")
                elif "Страна" in label:
                    country = value.strip(", ")
                elif "Действующее вещество" in label:
                    substance = value.strip(", ")

            results.append(Product(
                name=name,
                price=price,
                link=link,
                image_url=image_url,
                manufacturer=manufacturer,
                country=country,
                substance=substance
            ))

        except Exception as e:
            print(f"Ошибка при обработке карточки: {e}")

    return results


async def async_search(query: str):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, parse_products, query)


@app.get("/search", response_model=List[Product])
async def search(query: str = Query(..., alias="q")):
    try:
        products = await async_search(query)
        return JSONResponse(content=[p.dict() for p in products])
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
