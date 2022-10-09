import aiohttp

from bs4 import BeautifulSoup

import config  # pyright: reportMissingImports=false


async def fetch(url: str) -> bytes:
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            return await r.read()


async def get_overwatch_news(amount: int) -> list[dict[str, str]]:
    content = await fetch(config.overwatch["news"])
    page = BeautifulSoup(content, features="html.parser")

    news = page.find_all("blz-card", attrs={"slot": "gallery-items"})
    if news is None:
        raise Exception()

    news = list(news)[:amount]

    all_news = []
    for n in news:
        cur_news = {}
        cur_news["title"] = n.find("h4", attrs={"slot": "heading"}).get_text()
        cur_news["link"] = n["href"]
        cur_news["thumbnail"] = n.find("blz-image", attrs={"slot": "image"})["src"]
        all_news.append(cur_news)
    return all_news


async def get_overwatch_heroes() -> dict[str, dict[str, str]]:
    content = await fetch(config.overwatch["hero"])
    page = BeautifulSoup(content, features="html.parser")

    heroes = [h for h in page.find_all("blz-hero-card", class_="heroCard")]

    all_heroes = {}
    for h in heroes:
        value = {}
        card_name = h.find("div", class_="heroCardName")
        value["name"] = card_name.find("span").get_text()
        value["portrait"] = h.find("blz-image", class_="heroCardPortrait")["src"]
        value["role"] = str(h["data-role"]).lower()
        key = str(h["data-hero-id"]).lower()
        all_heroes[key] = value

    return all_heroes
