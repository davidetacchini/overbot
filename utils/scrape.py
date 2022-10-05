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

    heroes = [h for h in page.find_all("blz-hero-card", class_="heroCard")]

    all_heroes = {}
    for h in heroes:
        value = {}
        card_name = h.find("div", class_="heroCardName")
        value["name"] = card_name.find("span").get_text()
        value["portrait"] = h.find("blz-image", class_="heroCardPortrait")["src"]
        key = str(h["data-hero-id"]).lower()
        # await _add_hero_details(key, value)
        all_heroes[key] = value

    return all_heroes


async def _add_hero_details(key: str, value: dict[str, str]) -> None:
    content = await fetch(config.overwatch["hero"] + f"/{key}")
    page = BeautifulSoup(content, features="html.parser")

    # overview tab
    value["role"] = page.find("h4", class_="hero-detail-role-name").get_text().lower()
    value["description"] = page.find("p", class_="hero-detail-description").get_text()
    # stars can be max 3, so we subtract empty stars to all stars to find the difficulty
    value["difficulty"] = 3 - len(page.find_all("span", class_="star m-empty"))

    to_check = (("weapons", "hero-ability-weapon"), ("abilities", "hero-ability"))
    for category, children in to_check:
        value[category] = []
        cat = page.find("div", class_=category)
        cat_children = cat.findChildren("div", class_=children)
        if not len(cat_children):
            name = cat.find("h4", class_="hero-ability-name").get_text()
            description = cat.find("p", class_="hero-ability-description").get_text()
            value[category].append((name, description))
        else:
            for what in page.find("div", class_=category).findChildren("div", class_=children):
                name = what.find("h4", class_="hero-ability-name").get_text()
                description = what.find("p", class_="hero-ability-description").get_text()
                value[category].append((name, description))
