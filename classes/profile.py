from __future__ import annotations

import re

from typing import TYPE_CHECKING, Any
from datetime import date

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
    "damage": emojis.damage,
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
        return self.data["icon"]

    @staticmethod
    def _to_pascal(key: str) -> str:
        """From camel case to pascal case (testTest -> Test Test)."""
        return (
            re.sub("([a-z])([A-Z])", r"\g<1> \g<2>", key)
            .replace(" Avg Per10Min", "")
            .replace(" Most In Game", "")
            .title()
        )

    @staticmethod
    def _get_rating_icon(rating: int) -> discord.PartialEmoji:
        if 0 < rating < 1500:
            return emojis.bronze
        elif 1500 <= rating < 2000:
            return emojis.silver
        elif 2000 <= rating < 2500:
            return emojis.gold
        elif 2500 <= rating < 3000:
            return emojis.platinum
        elif 3000 <= rating < 3500:
            return emojis.diamond
        elif 3500 <= rating < 4000:
            return emojis.master
        return emojis.grand_master

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

    async def save_ratings(self, profile_id: int, **kwargs: Any) -> None:
        tank = kwargs.get("tank", 0)
        damage = kwargs.get("damage", 0)
        support = kwargs.get("support", 0)

        query = """SELECT tank, damage, support
                   FROM rating
                   INNER JOIN profile
                           ON profile.id = rating.profile_id
                   WHERE profile.id = $1
                   AND rating.date = $2;
                """

        requested_at = date.today()
        roles = await self.bot.pool.fetch(query, profile_id, requested_at)

        if roles:
            # Assuming a user uses `/profile ratings` multiple times within
            # the same day, we don't want duplicate ratings. If only 1 rating
            # differs, then we insert the new ratings into the database.
            all_equals = False
            for t, d, s in roles:
                if t == tank and d == damage and s == support:
                    all_equals = True

        if not roles or not all_equals:  # type: ignore # all equals will be bound
            query = (
                "INSERT INTO rating (tank, damage, support, profile_id) VALUES ($1, $2, $3, $4);"
            )
            await self.bot.pool.execute(query, tank, damage, support, profile_id)

    def resolve_ratings(self) -> None | dict[str, int]:
        if not self.data["ratings"]:
            return None
        ratings = {}
        for key, value in self.data["ratings"].items():
            ratings[key.lower()] = value["level"]
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
            rating_icon = self._get_rating_icon(value)
            embed.add_field(
                name=f"{role_icon} {role_name}",
                value=f"{rating_icon} {value}{emojis.sr}",
            )
        embed.set_footer(
            text="Average: {average}".format(average=self.data.get("rating")),
            icon_url=self.data.get("ratingIcon"),
        )

        if save and profile_id is not None:
            await self.save_ratings(profile_id, **ratings)

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
                rating_icon = self._get_rating_icon(value)
                ratings_.append(f"{role_icon} {rating_icon}{value}{emojis.sr}")
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
