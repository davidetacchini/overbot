from __future__ import annotations

from typing import TYPE_CHECKING

from discord.app_commands import Choice

from . import emojis

if TYPE_CHECKING:
    from discord import Embed, Interaction, PartialEmoji


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


async def hero_autocomplete(interaction: Interaction, current: str):
    # Just slice the list to return the first 25 heroes since the
    # limit of displayable choices is 25 whereas the heroes are 32.
    heroes = interaction.client.heroes
    # The api uses different names for these heroes.
    values = {
        "soldier-76": "soldier76",
        "wrecking-ball": "wreckingBall",
        "dva": "dVa",
    }
    return [
        Choice(name=hero, value=values.get(hero, hero))
        for hero in heroes
        if current.lower() in hero.lower()
    ][:25]


async def module_autocomplete(interaction: Interaction, current: str):
    modules = interaction.client.extensions
    return [
        Choice(name=module, value=module) for module in modules if current.lower() in module.lower()
    ]
