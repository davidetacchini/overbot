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
