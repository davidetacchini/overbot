from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord

from aiohttp import ClientSession
from discord import app_commands
from discord.ext import commands

from classes.ui import BaseView
from utils.cache import cache
from utils.checks import is_premium
from utils.scrape import get_overwatch_news
from utils.helpers import map_autocomplete, hero_autocomplete, gamemode_autocomplete
from classes.exceptions import UnknownError

if TYPE_CHECKING:
    from asyncpg import Record

    from bot import OverBot


class HeroInfoView(BaseView):
    def __init__(self, *, interaction: discord.Interaction, data: dict[str, Any]) -> None:
        super().__init__(interaction=interaction)
        self.data = data

    @discord.ui.button(label="Abilities", style=discord.ButtonStyle.blurple)
    async def abilities(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        abilities = self.data.get("abilities")
        if not abilities:
            return

        pages = []
        for index, ability in enumerate(abilities, start=1):
            embed = discord.Embed()
            embed.set_author(name=self.data.get("name"), icon_url=self.data.get("portrait"))
            embed.title = ability.get("name")
            embed.url = ability.get("video").get("link").get("mp4")
            embed.description = ability.get("description")
            embed.set_thumbnail(url=ability.get("icon"))
            embed.set_image(url=ability.get("video").get("thumbnail"))
            embed.set_footer(text=f"Page {index} of {len(abilities)}")
            pages.append(embed)

        await interaction.client.paginate(pages, interaction=interaction)

    @discord.ui.button(label="Story", style=discord.ButtonStyle.blurple)
    async def story(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        story = self.data.get("story")
        if not story:
            return

        chapters = story.get("chapters")
        max_pages = len(chapters) + 1
        pages = []

        embed = discord.Embed()
        embed.set_author(name=self.data.get("name"), icon_url=self.data.get("portrait"))
        embed.url = story.get("media").get("link")
        embed.title = "Origin Story"
        embed.description = story.get("summary")
        embed.set_footer(text=f"Page 1 of {max_pages}")
        pages.append(embed)

        for index, chapter in enumerate(story.get("chapters"), start=2):
            embed = discord.Embed()
            embed.set_author(name=self.data.get("name"), icon_url=self.data.get("portrait"))
            embed.title = chapter.get("title")
            embed.description = chapter.get("content")
            embed.set_image(url=chapter.get("picture"))
            embed.set_footer(text=f"Page {index} of {max_pages}")
            pages.append(embed)

        await interaction.client.paginate(pages, interaction=interaction)

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class Newsboard:
    __slots__ = ("guild_id", "bot", "record", "channel_id", "member_id")

    def __init__(self, guild_id: int, bot: OverBot, *, record: None | Record = None) -> None:
        self.guild_id = guild_id
        self.bot = bot
        self.channel_id: None | int = None

        if record:
            self.channel_id = record["id"]
            self.member_id: int = record["member_id"]

    @property
    def channel(self) -> None | discord.TextChannel:
        guild = self.bot.get_guild(self.guild_id)
        return guild and guild.get_channel(self.channel_id)


class Overwatch(commands.Cog):
    def __init__(self, bot: OverBot) -> None:
        self.bot = bot

    info = app_commands.Group(
        name="info", description="Provides information about heroes, maps or gamemodes."
    )

    @app_commands.command()
    async def status(self, interaction: discord.Interaction) -> None:
        """Returns Overwatch server status link"""
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.description = f"[Overwatch Servers Status]({self.bot.config.overwatch['status']})"
        embed.set_footer(text="downdetector.com")
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: i.user.id)
    async def news(self, interaction: discord.Interaction) -> None:
        """Shows the latest Overwatch news"""
        pages = []

        try:
            news = await get_overwatch_news()
        except Exception:
            embed = discord.Embed(color=self.bot.color(interaction.user.id))
            url = self.bot.config.overwatch["news"]
            embed.description = f"[Latest Overwatch News]({url})"
            await interaction.response.send_message(embed=embed)
            return

        for i, n in enumerate(news, start=1):
            embed = discord.Embed(color=self.bot.color(interaction.user.id))
            embed.title = n["title"]
            embed.url = n["link"]
            embed.set_author(name="Blizzard Entertainment")
            embed.set_image(url=n["thumbnail"])
            embed.set_footer(
                text="News {current}/{total} - {date}".format(
                    current=i, total=len(news), date=n["date"]
                )
            )
            pages.append(embed)

        await self.bot.paginate(pages, interaction=interaction)

    @app_commands.command()
    async def patch(self, interaction: discord.Interaction) -> None:
        """Returns Overwatch patch notes links"""
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.title = "Overwatch Patch Notes"
        categories = ("Live", "PTR", "Experimental", "Beta")
        description = []
        for category in categories:
            link = self.bot.config.overwatch["patch"].format(category.lower())
            description.append(f"[{category}]({link})")
        embed.description = " - ".join(description)
        await interaction.response.send_message(embed=embed)

    @cache()
    async def get_newsboard(self, guild_id: int) -> Newsboard:
        query = "SELECT * FROM newsboard WHERE server_id = $1;"
        record = await self.bot.pool.fetchrow(query, guild_id)
        return Newsboard(guild_id, self.bot, record=record)

    async def _has_newsboard(self, member_id: int) -> None | discord.Guild:
        query = "SELECT server_id FROM newsboard WHERE member_id = $1;"
        guild_id = await self.bot.pool.fetchval(query, member_id)
        return self.bot.get_guild(guild_id)

    @app_commands.command(extras=dict(premium=True))
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.guild_only()
    @is_premium()
    async def newsboard(self, interaction: discord.Interaction) -> None:
        """Creates an Overwatch news channel"""
        await interaction.response.defer(thinking=True)
        newsboard = await self.get_newsboard(interaction.guild_id)
        if newsboard.channel is not None:
            await interaction.followup.send(
                f"This server already has a newsboard at {newsboard.channel.mention}."
            )
            return

        if guild := await self._has_newsboard(interaction.user.id):
            payload = f"You have already set up a newsboard in **{str(guild)}**. Do you want to override it?"
            if await self.bot.prompt(interaction, payload):
                query = "DELETE FROM newsboard WHERE member_id = $1;"
                await self.bot.pool.execute(query, interaction.user.id)
                self.get_newsboard.invalidate(self, interaction.guild_id)
            else:
                return

        name = "overwatch-news"
        topic = "Latest Overwatch news."
        overwrites = {
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, embed_links=True
            ),
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=True, send_messages=False, read_message_history=True
            ),
        }
        reason = f"{interaction.user} created a text channel #overwatch-news"

        try:
            channel = await interaction.guild.create_text_channel(
                name=name, overwrites=overwrites, topic=topic, reason=reason
            )
        except discord.HTTPException:
            await interaction.followup.send("Something bad happened. Please try again.")
            return

        query = "INSERT INTO newsboard (id, server_id, member_id) VALUES ($1, $2, $3);"
        await self.bot.pool.execute(query, channel.id, interaction.guild_id, interaction.user.id)
        await interaction.followup.send(f"Channel successfully created at {channel.mention}.")

    async def embed_map_info(self, map_: str) -> discord.Embed:
        embed = discord.Embed()
        map_ = self.bot.maps.get(map_)
        embed.title = map_.get("name")
        embed.set_image(url=map_.get("screenshot"))
        gamemodes = "\n".join(map(lambda m: m.capitalize(), map_.get("gamemodes")))
        embed.add_field(name="Gamemodes", value=gamemodes)
        embed.add_field(name="Location", value=map_.get("location"))
        embed.add_field(name="Country Code", value=map_.get("country_code", "N/A"))
        return embed

    async def embed_gamemode_info(self, gamemode: str) -> discord.Embed:
        embed = discord.Embed()
        gamemode = self.bot.gamemodes.get(gamemode)
        embed.title = gamemode.get("name")
        embed.description = gamemode.get("description")
        embed.set_thumbnail(url=gamemode.get("icon"))
        embed.set_image(url=gamemode.get("screenshot"))
        return embed

    @info.command()
    @app_commands.autocomplete(name=hero_autocomplete)
    @app_commands.describe(name="The name of the hero to see information for")
    async def hero(self, interaction: discord.Interaction, name: str) -> None:
        """Returns information about a given hero"""
        url = f"{self.bot.BASE_URL}/heroes/{name}"
        async with ClientSession() as s:
            async with s.get(url) as r:
                if r.status != 200:
                    raise UnknownError()
                data = await r.json()

        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.set_author(name=data.get("name"), icon_url=data.get("portrait"))
        embed.description = data.get("description")
        hitpoints = "\n".join(
            f"{k.capitalize()}: **{v}**" for k, v in data.get("hitpoints").items()
        )
        embed.add_field(name="Hitpoints", value=hitpoints)
        embed.add_field(name="Role", value=data.get("role").capitalize())
        embed.add_field(name="Location", value=data.get("location"))

        view = HeroInfoView(interaction=interaction, data=data)
        await interaction.response.send_message(embed=embed, view=view)

    @info.command()
    @app_commands.autocomplete(name=map_autocomplete)
    @app_commands.describe(name="The name of the map to see information for")
    async def map(self, interaction: discord.Interaction, name: str) -> None:
        """Returns information about a given map"""
        embed = await self.embed_map_info(name)
        await interaction.response.send_message(embed=embed)

    @info.command()
    @app_commands.autocomplete(name=gamemode_autocomplete)
    @app_commands.describe(name="The name of the gamemode to see information for")
    async def gamemode(self, interaction: discord.Interaction, name: str) -> None:
        """Returns information about a given gamemode"""
        embed = await self.embed_gamemode_info(name)
        await interaction.response.send_message(embed=embed)


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Overwatch(bot))
