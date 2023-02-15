from __future__ import annotations

import re

from typing import TYPE_CHECKING, Any

import discord

from aiohttp.client_exceptions import ClientConnectorError

from utils import emojis

from .request import Request
from .exceptions import NoStats, NoHeroStats, UnexpectedError

if TYPE_CHECKING:
    from asyncpg import Record

    from bot import OverBot

    Stat = dict[str, None | dict[str, Any]]

ROLES = {
    "tank": emojis.tank,
    "offense": emojis.offense,
    "support": emojis.support,
}


class Profile:
    __slots__ = ("data", "id", "platform", "username", "interaction", "record", "bot", "pages")

    def __init__(
        self,
        platform: None | str = None,
        username: None | str = None,
        *,
        interaction: discord.Interaction,
        record: None | Record = None,
    ) -> None:
        self.data: dict[str, Any] = {}
        self.id: None | int = None

        if record:
            self.id = record["id"]
            self.platform = record["platform"]
            self.username = record["username"]
        else:
            self.platform = platform
            self.username = username

        self.interaction = interaction
        self.bot: OverBot = interaction.client
        self.pages: list[discord.Embed] = []

    def __str__(self) -> str:
        return self.data["name"]

    @property
    def avatar(self) -> str:
        if icon := self.data["icon"]:
            return icon
        else:
            "https://imgur.com/a/BrDrZKL"

    @staticmethod
    def _to_pascal(key: str) -> str:
        """From camel case to pascal case (testTest -> Test Test)."""
        return (
            re.sub("([a-z])([A-Z])", r"\g<1> \g<2>", key)
            .replace(" Avg Per10Min", "")
            .replace(" Most In Game", "")
            .title()
        )

    def _format_key(self, key: str) -> str:
        match key:
            case "best":
                return key.capitalize() + " (Most in game)"
            case "average":
                return key.capitalize() + " (per 10 minutes)"
            case _:
                return self._to_pascal(key)

    async def compute_data(self) -> None:
        try:
            self.data = await Request(self.platform, self.username).get()
        except ClientConnectorError:
            raise UnexpectedError() from None

    def is_private(self) -> bool:
        return self.data["private"]

    def resolve_ratings(self) -> None | dict[str, int]:
        if not self.data["ratings"]:
            return None
        ratings = {}
        for key, value in self.data["ratings"].items():
            ratings[key.lower()] = f"**{value['group']} {str(value['tier'])}**"
        return ratings

    def _resolve_stats(self, hero: str) -> None | tuple[list[str], Stat, Stat]:
        # OwAPI uses different names for these heroes.
        lookup = {
            "soldier-76": "soldier76",
            "wrecking-ball": "wreckingBall",
            "dva": "dVa",
        }
        alias = lookup.get(hero, hero)

        # quickplay stats
        q = self.data.get("quickPlayStats").get("careerStats").get(alias) or {}
        # competitive stats
        c = self.data.get("competitiveStats").get("careerStats").get(alias) or {}

        if not q and not c:
            if hero == "allHeroes":
                raise NoStats()
            else:
                raise NoHeroStats(hero)

        keys = list({*q, *c})
        keys.sort()

        for i, key in enumerate(keys):
            if not q.get(key) and not c.get(key):
                del keys[i]

        return keys, q, c

    def _format_stats(
        self,
        embed: discord.Embed,
        key: str,
        quickplay: Stat,
        competitive: Stat,
    ) -> None:
        if quickplay and quickplay[key] is not None:
            q_t = "\n".join(f"{k}: **{v}**" for k, v in quickplay[key].items())
            embed.add_field(name="Quick Play", value=self._to_pascal(q_t))
        if competitive and competitive[key] is not None:
            c_t = "\n".join(f"{k}: **{v}**" for k, v in competitive[key].items())
            embed.add_field(name="Competitive", value=self._to_pascal(c_t))

    async def embed_ratings(
        self, *, save: bool = False, profile_id: None | int = None
    ) -> discord.Embed:
        embed = discord.Embed(color=self.bot.color(self.interaction.user.id))
        embed.set_author(name=str(self), icon_url=self.avatar)

        ratings = self.resolve_ratings()

        if not ratings:
            embed.description = "This profile is unranked."
            return embed

        for key, value in ratings.items():
            role_icon = ROLES.get(key)
            role_name = key.upper()
            embed.add_field(name=f"{role_icon} {role_name}", value=value)

        return embed

    def embed_stats(self, hero: str) -> list[discord.Embed]:
        keys, quickplay, competitive = self._resolve_stats(hero)

        for i, key in enumerate(keys, start=1):
            embed = discord.Embed(color=self.bot.color(self.interaction.user.id))
            embed.title = self._format_key(key)
            embed.set_author(name=str(self), icon_url=self.avatar)
            if hero != "allHeroes":
                embed.set_thumbnail(url=self.bot.config.hero_portrait_url.format(hero.lower()))
            embed.set_footer(text=f"Page {i} of {len(keys)}")
            self._format_stats(embed, key, quickplay, competitive)
            self.pages.append(embed)
        return self.pages

    def embed_summary(self) -> discord.Embed:
        embed = discord.Embed(color=self.bot.color(self.interaction.user.id))
        embed.set_author(name=str(self), icon_url=self.avatar)

        ratings = self.resolve_ratings()

        if ratings:
            ratings_ = []
            for key, value in ratings.items():
                role_icon = ROLES.get(key.lower())
                ratings_.append(f"{role_icon} {value}")
            embed.description = " ".join(ratings_)

        summary = {}
        summary["endorsement"] = self.data.get("endorsement")
        summary["gamesWon"] = self.data.get("gamesWon")

        for key, value in summary.items():
            embed.add_field(name=self._to_pascal(key), value=value)

        def format_dict(source: Stat) -> dict[str, Any]:
            d = {}
            d["game"] = source.get("game")
            to_keep = ("deaths", "eliminations", "damageDone")
            d["combat"] = {k: v for k, v in source.get("combat").items() if k in to_keep}
            d["awards"] = source.get("matchAwards")
            return d

        def format_embed(source: dict[str, Any], embed: discord.Embed, *, category: str) -> None:
            for key, value in source.items():
                key = f"{self._to_pascal(key)} ({category.title()})"
                if isinstance(value, dict):
                    v = "\n".join(f"{k}: **{v}**" for k, v in value.items())
                    embed.add_field(name=key, value=self._to_pascal(v))
                else:
                    embed.add_field(name=key, value=value)

        q = self.data.get("quickPlayStats").get("careerStats").get("allHeroes")  # quick play
        c = self.data.get("competitiveStats").get("careerStats").get("allHeroes")  # competitive

        if q:
            quickplay = format_dict(q)
            format_embed(quickplay, embed, category="quick play")

        if c:
            competitive = format_dict(c)
            format_embed(competitive, embed, category="competitive")

        return embed

    def embed_private(self) -> discord.Embed:
        embed = discord.Embed(color=discord.Color.red())
        embed.title = "This profile is set to private"
        embed.description = (
            "Profiles are set to private by default."
            " You can modify this setting in Overwatch under `Options > Social`."
            " Please note that this change may take effect within approximately 30 minutes."
        )
        embed.set_author(name=str(self), icon_url=self.avatar)
        return embed
