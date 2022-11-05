from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from discord import app_commands
from discord.ext import commands

from utils.cache import cache
from utils.checks import is_premium
from utils.scrape import get_overwatch_news

if TYPE_CHECKING:
    from asyncpg import Record

    from bot import OverBot


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

    @app_commands.command()
    async def status(self, interaction: discord.Interaction) -> None:
        """Returns Overwatch server status link"""
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.description = f"[Overwatch Servers Status]({self.bot.config.overwatch['status']})"
        embed.set_footer(text="downdetector.com")
        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    @app_commands.describe(amount="The amount of news to return. Defaults to 4")
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: i.user.id)
    async def news(
        self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 4] = 4
    ) -> None:
        """Shows the latest Overwatch news"""
        pages = []

        try:
            news = await get_overwatch_news(amount)
        except Exception:
            embed = discord.Embed(color=self.bot.color(interaction.user.id))
            url = self.bot.config.overwatch["news"]
            embed.description = f"[Latest Overwatch News]({url})"
            return await interaction.response.send_message(embed=embed)

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
            return await interaction.followup.send(
                f"This server already has a newsboard at {newsboard.channel.mention}."
            )

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
            return await interaction.followup.send("Something bad happened. Please try again.")

        query = "INSERT INTO newsboard (id, server_id, member_id) VALUES ($1, $2, $3);"
        await self.bot.pool.execute(query, channel.id, interaction.guild_id, interaction.user.id)
        await interaction.followup.send(f"Channel successfully created at {channel.mention}.")


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Overwatch(bot))
