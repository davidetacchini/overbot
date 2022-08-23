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

    news = page.find("section", class_="NewsHeader-featured")
    if news is None:
        raise Exception()

    news = list(news)[:amount]

    all_news = []
    for n in news:
        cur_news = {}
        cur_news["title"] = n.find("h1", {"class": "Card-title"}).get_text()
        cur_news["link"] = "https://playoverwatch.com" + n["href"]
        cur_news["thumbnail"] = n.find("div", class_="Card-thumbnail")["style"].split("url(")[1][
            :-1
        ]
        cur_news["date"] = n.find("p", class_="Card-date").get_text()
        all_news.append(cur_news)
    return all_news


async def get_overwatch_maps() -> list[dict[str, str | list[str]]]:
    content = await fetch(config.overwatch["map"])
    page = BeautifulSoup(content, features="html.parser")

    maps = [m for m in page.find_all("figure", class_="Card")]

    all_maps = []
    for m in maps:
        cur_map = {}
        cur_map["name"] = m.find("h5", class_="Card-title").get_text()
        categories = []
        for div in m.find_all("div", class_="MapType-tooltip"):
            categories.append(div["data-ow-tooltip-text"].lower())
        cur_map["types"] = categories
        all_maps.append(cur_map)
    return all_maps


async def get_overwatch_heroes() -> dict[str, dict[str, str]]:
    content = await fetch(config.overwatch["hero"])
    page = BeautifulSoup(content, features="html.parser")

    heroes = [h for h in page.find_all("div", class_="hero-portrait-detailed-container")]

    all_heroes = {}
    for h in heroes:
        value = {}
        value["name"] = h.find("span", class_="portrait-title").get_text()
        value["portrait"] = h.find("img", class_="portrait")["src"]
        value["role"] = h["data-groups"][2:-2].lower()
        key = str(h.find("a", class_="hero-portrait-detailed")["data-hero-id"]).lower()
        all_heroes[key] = value
    return all_heroes
