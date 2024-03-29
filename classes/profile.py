from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

import discord
from aiohttp.client_exceptions import ClientConnectorError

from utils import emojis

from .exceptions import NoStats, UnknownError
from .request import Request

if TYPE_CHECKING:
    from asyncpg import Record

    from bot import OverBot


ROLE_TO_EMOJI = {
    "tank": emojis.tank,
    "damage": emojis.damage,
    "support": emojis.support,
}


class Profile:
    __slots__ = (
        "id",
        "battletag",
        "interaction",
        "record",
        "bot",
        "pages",
        "_platforms",
        "_data",
    )

    def __init__(
        self,
        battletag: None | str = None,
        *,
        interaction: discord.Interaction,
        record: None | Record = None,
    ) -> None:
        self.id: None | int = None

        if record:
            self.id = record["id"]
            self.battletag = record["battletag"]
        else:
            self.battletag = battletag

        self.interaction = interaction
        self.bot: OverBot = getattr(interaction, "client")
        self.pages: list[discord.Embed] = []

        self._platforms: tuple[str, ...] = ("pc", "console")
        self._data: dict[str, Any] = {}

    @property
    def request(self) -> Request:
        return Request(self.battletag)  # type: ignore

    @property
    def _summary(self) -> dict[str, Any]:
        return self._safe_get(self._data, "summary")

    @property
    def _stats(self) -> dict[str, Any]:
        return self._safe_get(self._data, "stats")

    @property
    def username(self) -> str:
        return self._safe_get(self._summary, "username")

    @property
    def avatar(self) -> str:
        return self._safe_get(self._summary, "avatar", default="https://imgur.com/a/BrDrZKL")

    @property
    def namecard(self) -> None | str:
        return self._safe_get(self._summary, "namecard")

    @property
    def title(self) -> None | str:
        return self._safe_get(self._summary, "title", default="N/A")

    @property
    def endorsement(self) -> None | str:
        return self._safe_get(self._summary, "endorsement.level", default="N/A")

    @staticmethod
    def _format_key(key: str, *, only_capital: bool = False) -> str:
        match key:
            case "best":
                if only_capital:
                    return key.capitalize()
                return key.capitalize() + " (Most in game)"
            case "average":
                if only_capital:
                    return key.capitalize()
                return key.capitalize() + " (per 10 minutes)"
            case _:
                return (
                    key.replace("_", " ")
                    .title()
                    .replace(" Avg Per 10 Min", "")
                    .replace(" Most In Game", "")
                )

    @staticmethod
    def _safe_get(source: dict, path: str, /, *, default={}) -> Any:
        if "." not in path:
            return source.get(path)
        keys = path.split(".")
        ret = source
        for key in keys:
            ret = ret.get(key)
            if not ret:
                return default
        return ret

    @staticmethod
    def _from_list_to_dict(source: list[dict[str, Any]]) -> dict[str, Any]:
        career_stats = {}
        for item in source:
            stats = {}
            for stat in item["stats"]:
                stats[stat["key"]] = stat["value"]
            career_stats[item.pop("category")] = stats
        return career_stats

    async def fetch_data(self) -> None:
        try:
            self._data = await self.request.fetch_data()
        except ClientConnectorError:
            raise UnknownError() from None

    def is_private(self) -> bool:
        return self._summary.get("privacy") == "private"

    def _resolve_ratings(self, *, platform: str) -> None | dict[str, int]:
        raw_ratings = self._safe_get(self._summary, f"competitive.{platform}")
        if not raw_ratings:
            return

        ratings = {}
        for key, value in raw_ratings.items():
            if not value or isinstance(value, int):  # skip null values and 'season' value
                continue
            ratings[key.lower()] = f"**{value['division'].capitalize()} {str(value['tier'])}**"
        return ratings

    def _resolve_stats(
        self, platform: str, hero: str, /
    ) -> None | tuple[list[str], dict[str, Any], dict[str, Any]]:
        q = self._safe_get(self._stats, f"{platform}.quickplay.career_stats.{hero}")
        q = self._from_list_to_dict(q)
        c = self._safe_get(self._stats, f"{platform}.competitive.career_stats.{hero}")
        c = self._from_list_to_dict(c)

        if not q and not c:
            return

        keys = list({*q, *c})
        keys.sort()

        return keys, q, c

    def _format_stats(
        self,
        embed: discord.Embed,
        key: str,
        quick: dict[str, Any],
        competitive: dict[str, Any],
    ) -> None:
        if quick and quick.get(key) is not None:
            q_temp = "\n".join(f"{k}: **{v}**" for k, v in quick[key].items())
            embed.add_field(name="Quick Play", value=self._format_key(q_temp))
        if competitive and competitive.get(key) is not None:
            c_temp = "\n".join(f"{k}: **{v}**" for k, v in competitive[key].items())
            embed.add_field(name="Competitive", value=self._format_key(c_temp))

    def embed_ratings(self) -> dict[str, discord.Embed]:
        ratings = {}
        for platform in self._platforms:
            embed = discord.Embed(color=self.bot.color(self.interaction.user.id))
            username = f"{self.username} [{platform.upper()}]"
            embed.set_author(name=username, icon_url=self.avatar)

            raw_ratings = self._resolve_ratings(platform=platform)

            if not raw_ratings:
                embed.description = "This profile is unranked."
            else:
                for key, value in raw_ratings.items():
                    role_icon = ROLE_TO_EMOJI.get(key)
                    role_name = key.upper()
                    embed.add_field(name=f"{role_icon} {role_name}", value=value)

            ratings[platform] = embed
        return ratings

    def embed_stats(self, hero: str) -> dict[str, discord.Embed | list[discord.Embed]]:
        stats = {}
        for platform in self._platforms:
            embed = discord.Embed(color=self.bot.color(self.interaction.user.id))
            username = f"{self.username} [{platform.upper()}]"
            embed.set_author(name=username, icon_url=self.avatar)

            career_stats = self._resolve_stats(platform, hero)
            if career_stats is None:
                embed.description = "There is no data for this account in this mode yet."
                stats[platform] = embed
                continue

            self.pages = []
            keys, quick, competitive = career_stats
            for i, key in enumerate(keys, start=1):
                embed_copy = embed.copy()
                embed_copy.title = self._format_key(key)
                if hero != "all-heroes":
                    embed_copy.set_thumbnail(url=self.bot.heroes[hero]["portrait"])
                embed_copy.set_footer(text=f"Page {i} of {len(keys)}")
                self._format_stats(embed_copy, key, quick, competitive)
                self.pages.append(embed_copy)
            stats[platform] = self.pages

        # if both console and pc just have an embed that means there are no stats
        if isinstance(stats["pc"], discord.Embed) and isinstance(stats["console"], discord.Embed):
            raise NoStats(hero)
        return stats

    async def embed_summary(self) -> discord.Embed:
        embed = discord.Embed(color=self.bot.color(self.interaction.user.id))
        embed.set_author(name=self.username, icon_url=self.avatar)
        embed.set_image(url=self.namecard)
        embed.set_footer(text=f"Endorsement: {self.endorsement}")

        def format_dict(source: dict[str, Any]):
            for key, value in source.items():
                if key == "time_played":
                    value = str(datetime.timedelta(seconds=value))
                if isinstance(value, dict):
                    value = "\n".join(f"{self._format_key(k)}: **{v}**" for k, v in value.items())
                embed.add_field(name=self._format_key(key, only_capital=True), value=value)

        def get_most_played_hero(source: Any):
            name, time_played = "N/A", 0
            for key, value in source.items():
                if (cur_time := value.get("time_played")) > time_played:
                    name, time_played = key, cur_time
            conv_time = str(datetime.timedelta(seconds=time_played))
            embed.add_field(name="Most Played Hero", value=f"{name.capitalize()}: {conv_time}")

        try:
            data = await self.request.fetch_stats_summary()
        except ClientConnectorError:
            raise UnknownError() from None

        general = data.get("general") or {}
        heroes = data.get("heroes") or {}

        if general:
            format_dict(general)
        if heroes:
            get_most_played_hero(heroes)

        return embed

    def embed_private(self) -> discord.Embed:
        embed = discord.Embed(color=discord.Color.red())
        embed.set_author(name=self.username, icon_url=self.avatar)
        embed.title = "This profile is currently private"
        embed.description = (
            "Profiles are set to private by default."
            " You can update the profile visibility in Overwatch 2 settings."
            " Depending on Blizzard servers this change could take effect"
            " in minutes or it could take days."
        )
        return embed
