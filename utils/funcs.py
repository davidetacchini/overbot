from discord import Embed, PartialEmoji

from . import emojis


def get_platform_emoji(platform: str) -> PartialEmoji:
    lookup = {
        "pc": emojis.battlenet,
        "psn": emojis.psn,
        "xbl": emojis.xbl,
        "nintendo-switch": emojis.switch,
    }
    return lookup[platform]


async def chunker(pages: str | dict | Embed, *, per_page: int):
    for x in range(0, len(pages), per_page):
        yield pages[x : x + per_page]
