import aiohttp

from bs4 import BeautifulSoup

import config  # pyright: reportMissingImports=false


async def fetch(url: str) -> bytes:
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            return await r.read()


async def get_overwatch_news(amount: int) -> list[dict[str, str]]:
    with open("assets/latest_news_id.txt", "r") as fp:
        news_id = fp.readline()

    content = await fetch(config.overwatch["news"] + str(news_id))
    page = BeautifulSoup(content, features="html.parser")

    news = page.find_all("a", {"class": "media@lg-min"})
    if news is None:
        raise Exception()

    news = list(news)[:amount]

    all_news = []
    for n in news:
        cur_news = {}
        cur_news["title"] = n.find("h3", class_="blog-sidebar-article-title").get_text()
        cur_news["link"] = "https://overwatch.blizzard.com" + n["href"]
        cur_news["thumbnail"] = "https:" + n.find("img", class_="media-card-fill")["src"]
        cur_news["date"] = n.find("p", class_="blog-sidebar-date").get_text()
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
