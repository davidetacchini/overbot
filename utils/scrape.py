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
    titles = [x.get_text() for x in news.find_all("h1", {"class": "Card-title"})]
    links = ["https://playoverwatch.com" + x["href"] for x in news]
    imgs = [
        x["style"].split("url(")[1][:-1]
        for x in news.find_all("div", {"class", "Card-thumbnail"})
    ]
    dates = [x.get_text() for x in news.find_all("p", {"class": "Card-date"})]
    return titles[:amount], links[:amount], imgs[:amount], dates[:amount]


async def get_overwatch_patch_notes(ctx):
    locale = ctx.bot.locales[ctx.author.id]
    content = await fetch(config.overwatch["patch"].format(locale, ""))
    page = BeautifulSoup(content, features="html.parser")
    patch = page.find("div", {"class": "PatchNotes-types"})
    return [
        x.get_text() for x in patch.find_all("button", {"class": "PatchNotes-type"})
    ]


async def get_overwatch_maps(locale):
    content = await fetch(config.random["map"].format(locale))
    page = BeautifulSoup(content, features="html.parser")

    all_maps = []
    maps = [m for m in page.find_all("figure", {"class": "Card"})]

    for m in maps:
        cur_map = {}
        cur_map["name"] = m.find("h5", {"class": "Card-title"}).get_text()
        cur_map["image_url"] = m.find("img", {"class": "Card-thumbnail"})["src"]
        cur_map["flag_url"] = m.find("span", {"class": "Map-flag"}).img["src"]
        categories = []
        for div in m.find_all("div", {"class": "MapType-tooltip"}):
            categories.append(div["data-ow-tooltip-text"].lower())
        cur_map["types"] = categories
        all_maps.append(cur_map)
    return all_maps
