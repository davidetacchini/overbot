import aiohttp

from bs4 import BeautifulSoup

import config


async def fetch(url):
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            return await r.read()


async def get_overwatch_status():
    content = await fetch(config.overwatch["status"])
    page = BeautifulSoup(content, features="html.parser")
    return page.find(class_="entry-title").get_text()


async def get_overwatch_news(locale, *, amount):
    content = await fetch(config.overwatch["news"].format(locale))
    page = BeautifulSoup(content, features="html.parser")
    news = page.find("section", {"class", "NewsHeader-featured"})
    news = list(news)[:amount]

    all_news = []
    for n in news:
        cur_news = {}
        cur_news["title"] = n.find("h1", {"class": "Card-title"}).get_text()
        cur_news["link"] = "https://playoverwatch.com" + n["href"]
        cur_news["thumbnail"] = n.find("div", {"class", "Card-thumbnail"})[
            "style"
        ].split("url(")[1][:-1]
        cur_news["date"] = n.find("p", {"class": "Card-date"}).get_text()
        all_news.append(cur_news)
    return all_news


async def get_overwatch_patch_notes(locale):
    content = await fetch(config.overwatch["patch"].format(locale, ""))
    page = BeautifulSoup(content, features="html.parser")
    patch_notes = page.find("div", {"class": "PatchNotes-types"})
    types = patch_notes.find_all("button", {"class": "PatchNotes-type"})
    return [t.get_text() for t in types]


async def get_overwatch_maps():
    content = await fetch(config.overwatch["map"])
    page = BeautifulSoup(content, features="html.parser")

    maps = [m for m in page.find_all("figure", {"class": "Card"})]

    all_maps = []
    for m in maps:
        cur_map = {}
        cur_map["name"] = m.find("h5", {"class": "Card-title"}).get_text()
        categories = []
        for div in m.find_all("div", {"class": "MapType-tooltip"}):
            categories.append(div["data-ow-tooltip-text"].lower())
        cur_map["types"] = categories
        all_maps.append(cur_map)
    return all_maps


async def get_overwatch_heroes():
    content = await fetch(config.overwatch["hero"])
    page = BeautifulSoup(content, features="html.parser")

    heroes = [
        h for h in page.find_all("div", {"class": "hero-portrait-detailed-container"})
    ]

    all_heroes = []
    for h in heroes:
        cur_hero = {}
        cur_hero["key"] = h.find("a", {"class": "hero-portrait-detailed"})[
            "data-hero-id"
        ]
        cur_hero["name"] = h.find("span", {"class": "portrait-title"}).get_text()
        cur_hero["portrait"] = h.find("img", {"class": "portrait"})["src"]
        cur_hero["role"] = h["data-groups"][2:-2].lower()
        all_heroes.append(cur_hero)
    return all_heroes
