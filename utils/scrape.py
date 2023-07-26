import aiohttp

from bs4 import BeautifulSoup

import config


async def fetch(url: str) -> bytes:
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            return await r.read()


async def get_overwatch_news(amount: int) -> list[dict[str, str]]:
    with open("assets/latest_news_id.txt", "r") as fp:
        news_id = fp.readline()

    content = await fetch(config.overwatch["news"] + str(news_id))

    root_kwargs = {"name": "div", "class_": "main-content", "recursive": False}
    root = BeautifulSoup(content, features="lxml").body.find(**root_kwargs)

    news_container = root.find("div", class_="news-header", recursive=False).find(
        "blz-news", recursive=False
    )

    news = [
        {
            "title": n.find("h4", slot="heading").get_text(),
            "link": n["href"],
            "thumbnail": "https:" + n.find("blz-image", slot="image")["src"],
            "date": n["date"].split(":")[0][:-3],  # from YYYY-MM-DDT18:00:00.000Z to YYYY-MM-DD
        }
        for n in news_container.find_all("blz-card")
    ]
    return news
