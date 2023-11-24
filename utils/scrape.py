# type: ignore
from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp
from bs4 import BeautifulSoup

import config

if TYPE_CHECKING:
    News = list[dict[str, str]]


async def fetch(url: str) -> bytes:
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            return await r.read()


async def get_overwatch_news() -> News:
    content = await fetch(config.overwatch["news"])

    root_kwargs = {"name": "div", "class_": "main-content", "recursive": False}
    root = BeautifulSoup(content, features="lxml").body.find(**root_kwargs)

    news_container = root.find("div", class_="news-header", recursive=False).find(
        "blz-news", recursive=False
    )

    news = [
        {
            "title": n.find("h4", slot="heading").get_text(),
            "link": "https://overwatch.blizzard.com/en-us" + n["href"],
            "thumbnail": "https:" + n.find("blz-image", slot="image")["src"],
            "date": n["date"].split(":")[0][:-3],  # from YYYY-MM-DDT18:00:00.000Z to YYYY-MM-DD
        }
        for n in news_container.find_all("blz-card")
    ]
    return news


async def get_overwatch_news_from_ids(ids: list[str]) -> News:
    news = []
    for idx in ids:
        url = config.overwatch["news"] + idx
        content = await fetch(url)

        root = BeautifulSoup(content, features="lxml")

        image = root.find("div", class_="blog-header-image")

        news.append(
            {
                "title": root.find("h1", class_="blog-title").get_text(),
                "link": url,
                "thumbnail": image.find("img")["src"],
                "date": root.find("span", class_="publish-date").get_text(),
            }
        )

    return news
