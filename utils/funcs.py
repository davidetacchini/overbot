from __future__ import annotations

from typing import TYPE_CHECKING

from discord.app_commands import Choice

from . import emojis

if TYPE_CHECKING:
    from discord import Interaction, PartialEmoji


platform_choices = [
    Choice(name="Battle.net", value="pc"),
    Choice(name="PlayStation", value="psn"),
    Choice(name="XBOX", value="xbl"),
    Choice(name="Nintendo Switch", value="nintendo-switch"),
]


def get_platform_emoji(platform: str) -> PartialEmoji:
    lookup = {
        "pc": emojis.battlenet,
        "psn": emojis.psn,
        "xbl": emojis.xbl,
        "nintendo-switch": emojis.switch,
    }
    return lookup[platform]


def format_platform(platform: str) -> str:
    lookup = {
        "pc": "Battle.net",
        "psn": "PlayStation",
        "xbl": "XBOX",
        "nintendo-switch": "Nintendo Switch",
    }
    return lookup[platform]


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


async def profile_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    profile_cog = interaction.client.get_cog("Profile")
    profiles = await profile_cog.get_profiles(interaction, interaction.user.id)
    return [
        Choice(name=f"{format_platform(profile.platform)} - {profile.username}", value=profile.id)
        for profile in profiles
        if current.lower() in profile.username.lower()
    ]
