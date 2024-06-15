from __future__ import annotations

import datetime
import json
import logging
from typing import TYPE_CHECKING, Any

import discord
from aiohttp.client_exceptions import ClientConnectorError
from discord import app_commands
from discord.ext import commands

from classes.exceptions import NoStats, UnknownError
from classes.profile import Profile
from classes.ui import PlatformSelectMenu
from utils import emojis
from utils.helpers import hero_autocomplete

if TYPE_CHECKING:
    from bot import OverBot

log = logging.getLogger(__name__)


ROLE_TO_EMOJI = {
    "tank": emojis.tank,
    "damage": emojis.damage,
    "support": emojis.support,
}


class Stats(commands.Cog):
    def __init__(self, bot: OverBot) -> None:
        self.bot = bot

    @staticmethod
    def format_key(key: str, *, only_capital: bool = False) -> str:
        if only_capital:
            return key.capitalize()

        match key:
            case "best":
                return key.capitalize() + " (Most in game)"
            case "average":
                return key.capitalize() + " (per 10 minutes)"
            case _:
                return (
                    key.replace("_", " ")
                    .title()
                    .replace(" Avg Per 10 Min", "")
                    .replace(" Most In Game", "")
                )

    async def save_stats(
        self, author_id: int, guild_id: None | int, battletag: str, data: dict[str, Any]
    ) -> None:
        query = """WITH today_stats AS (
                       SELECT 1
                       FROM stats
                       WHERE battletag = $3
                         AND date_trunc('day', CURRENT_TIMESTAMP) = date_trunc('day', created_at)
                   )
                   INSERT INTO stats (author_id, guild_id, battletag, data)
                   SELECT $1, $2, $3, $4
                   WHERE NOT EXISTS (SELECT 1 FROM today_stats);
                """
        try:
            await self.bot.pool.execute(
                query, author_id, guild_id, battletag.lower(), json.dumps(data)
            )
        except Exception as e:
            log.exception(f"Something bad happened while saving stats for {battletag}.\n{e}")
        else:
            # TODO: Stats for each BattleTag are saved once a day. If stats for a specific
            # BattleTag are already saved, it should not log this event. I need to refactor
            # the code to split the query into two separate queries. This will allow me to
            # determine if the stats have already been saved and avoid unnecessary logging.
            log.info(f"Stats successfully saved for {battletag}.")

    def format_stats(
        self,
        embed: discord.Embed,
        key: str,
        quick: dict[str, Any],
        competitive: dict[str, Any],
    ) -> None:
        if quick and quick.get(key) is not None:
            q_temp = "\n".join(f"{k}: **{v}**" for k, v in quick[key].items())
            embed.add_field(name="Quick Play", value=self.format_key(q_temp))
        if competitive and competitive.get(key) is not None:
            c_temp = "\n".join(f"{k}: **{v}**" for k, v in competitive[key].items())
            embed.add_field(name="Competitive", value=self.format_key(c_temp))

    async def embed_ratings(
        self, profile: Profile, *, interaction: discord.Interaction
    ) -> dict[str, discord.Embed]:
        ratings = {}
        for platform in profile.platforms:
            embed = discord.Embed(color=self.bot.get_user_color(interaction.user.id))
            username = f"{profile.username} [{platform.upper()}]"
            embed.set_author(name=username, icon_url=profile.avatar)

            raw_ratings = profile.get_ratings(platform=platform)

            if not raw_ratings:
                embed.description = "Unranked."
            else:
                for key, value in raw_ratings.items():
                    if key == "season":
                        embed.set_footer(text=f"Season: {value}")
                        continue
                    role_icon = ROLE_TO_EMOJI.get(key)
                    role_name = key.upper()
                    embed.add_field(name=f"{role_icon} {role_name}", value=value)

            ratings[platform] = embed
        return ratings

    async def embed_stats(
        self, profile: Profile, *, interaction: discord.Interaction, hero: str
    ) -> dict[str, discord.Embed | list[discord.Embed]]:
        stats = {}
        for platform in profile.platforms:
            embed = discord.Embed(color=self.bot.get_user_color(interaction.user.id))
            username = f"{profile.username} [{platform.upper()}]"
            embed.set_author(name=username, icon_url=profile.avatar)

            career_stats = profile.get_stats(platform=platform, hero=hero)
            if career_stats is None:
                embed.description = "There is no data for this account in this mode yet."
                stats[platform] = embed
                continue

            pages = []
            keys, quick, competitive = career_stats
            for i, key in enumerate(keys, start=1):
                embed_copy = embed.copy()
                embed_copy.title = self.format_key(key)
                if hero != "all-heroes":
                    embed_copy.set_thumbnail(url=self.bot.heroes[hero]["portrait"])
                embed_copy.set_footer(text=f"Page {i} of {len(keys)}")
                self.format_stats(embed_copy, key, quick, competitive)
                pages.append(embed_copy)
            stats[platform] = pages

        # if both console and pc just have an embed that means there are no stats
        if isinstance(stats["pc"], discord.Embed) and isinstance(stats["console"], discord.Embed):
            raise NoStats(hero)
        return stats

    async def embed_summary(
        self, profile: Profile, *, interaction: discord.Interaction
    ) -> discord.Embed:
        embed = discord.Embed(color=self.bot.get_user_color(interaction.user.id))
        embed.set_author(name=profile.username, icon_url=profile.avatar)
        embed.set_image(url=profile.namecard)
        embed.set_footer(text=f"Endorsement: {profile.endorsement}")

        def format_dict(source: dict[str, Any]):
            for key, value in source.items():
                if key == "time_played":
                    value = str(datetime.timedelta(seconds=value))
                if isinstance(value, dict):
                    value = "\n".join(f"{self.format_key(k)}: **{v}**" for k, v in value.items())
                embed.add_field(name=self.format_key(key, only_capital=True), value=value)

        def get_most_played_hero(source: Any):
            name, time_played = "N/A", 0
            for key, value in source.items():
                if (cur_time := value.get("time_played")) > time_played:
                    name, time_played = key, cur_time
            conv_time = str(datetime.timedelta(seconds=time_played))
            embed.add_field(name="Most Played Hero", value=f"{name.capitalize()}: {conv_time}")

        try:
            data = await profile.request.fetch_summary_data()
        except ClientConnectorError:
            raise UnknownError() from None

        general = data.get("general") or {}
        heroes = data.get("heroes") or {}

        if general:
            format_dict(general)
        if heroes:
            get_most_played_hero(heroes)

        return embed

    async def show_stats_for(
        self,
        interaction: discord.Interaction,
        hero: str,
        battletag: None | str = None,
        *,
        profile: None | Profile = None,
    ) -> None:
        profile = profile or Profile(battletag=battletag, session=self.bot.session)
        await profile.fetch_data()
        actual_battletag = battletag or profile.battletag
        await self.save_stats(
            interaction.user.id, interaction.guild_id, actual_battletag, profile._data  # type: ignore # can't be none
        )
        data = await self.embed_stats(profile, interaction=interaction, hero=hero)
        value = "console" if isinstance(data["pc"], discord.Embed) else "pc"
        view = PlatformSelectMenu(data[value], interaction=interaction)
        view.add_platforms(data)
        await view.start()

    @app_commands.command()
    @app_commands.describe(battletag="The battletag of the player")
    async def ratings(self, interaction: discord.Interaction, *, battletag: str) -> None:
        """Provides ratings for a player."""
        await interaction.response.defer(thinking=True)
        profile = Profile(battletag=battletag, session=self.bot.session)
        await profile.fetch_data()
        await self.save_stats(interaction.user.id, interaction.guild_id, battletag, profile._data)
        data = await self.embed_ratings(profile, interaction=interaction)
        value = "console" if isinstance(data["pc"], discord.Embed) else "pc"
        view = PlatformSelectMenu(data[value], interaction=interaction)
        view.add_platforms(data)
        await view.start()

    @app_commands.command()
    @app_commands.autocomplete(hero=hero_autocomplete)
    @app_commands.describe(battletag="The battletag of the player")
    @app_commands.describe(
        hero="The hero name to see the stats for. If not given then it shows general stats"
    )
    async def stats(
        self, interaction: discord.Interaction, *, battletag: str, hero: str = "all-heroes"
    ) -> None:
        """Provides general stats or hero specific stats for a player."""
        await interaction.response.defer(thinking=True)
        await self.show_stats_for(interaction, hero, battletag)

    @app_commands.command()
    @app_commands.describe(battletag="The battletag of the player")
    async def summary(self, interaction: discord.Interaction, *, battletag: str) -> None:
        """Provides summarized stats for a player.

        Data from both competitive and quickplay, and/or pc and console is merged.
        """
        await interaction.response.defer(thinking=True)
        profile = Profile(battletag=battletag, session=self.bot.session)
        await profile.fetch_data()
        await self.save_stats(interaction.user.id, interaction.guild_id, battletag, profile._data)
        embed = await self.embed_summary(profile, interaction=interaction)
        await interaction.followup.send(embed=embed)


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Stats(bot))
