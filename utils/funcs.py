from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncGenerator

from discord.app_commands import Choice

from . import emojis

if TYPE_CHECKING:
    from discord import Interaction, PartialEmoji

    A_Generator = AsyncGenerator[list[Any] | tuple[Any, ...], None]


def get_platform_emoji(platform: str) -> PartialEmoji:
    lookup = {
        "pc": emojis.battlenet,
        "psn": emojis.psn,
        "xbl": emojis.xbl,
        "nintendo-switch": emojis.switch,
    }
    return lookup[platform]


async def chunker(pages: list[Any] | tuple[Any], *, per_page: int) -> A_Generator:
    for x in range(0, len(pages), per_page):
        yield pages[x : x + per_page]  # noqa: E203


async def hero_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    heroes = interaction.client.heroes
    # The api uses different names for these heroes.
    values = {
        "soldier-76": "soldier76",
        "wrecking-ball": "wreckingBall",
        "dva": "dVa",
    }
    # Just slice the list to return the first 25 heroes since the
    # limit of displayable choices is 25 whereas the heroes are 32.
    return [
        Choice(name=hero, value=values.get(hero, hero))
        for hero in heroes
        if current.lower() in hero.lower()
    ][:25]


async def module_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    modules = interaction.client.extensions
    return [
        Choice(name=module, value=module) for module in modules if current.lower() in module.lower()
    ]
