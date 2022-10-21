from __future__ import annotations

import logging

from typing import TYPE_CHECKING
from datetime import datetime

import discord

from discord.ext import commands

if TYPE_CHECKING:
    from bot import OverBot

log = logging.getLogger("overbot")


class Events(commands.Cog):
    def __init__(self, bot: OverBot) -> None:
        self.bot = bot

    async def send_log(self, text: str, color: discord.Color) -> None:
        if self.bot.debug:
            return

        embed = discord.Embed(color=color)
        embed.title = text
        embed.timestamp = datetime.utcnow()
        await self.bot.webhook.send(embed=embed)

    async def send_guild_log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        """Sends information about a joined guild."""
        embed.title = guild.name
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        try:
            embed.add_field(name="Members", value=guild.member_count)
        except AttributeError:
            pass
        embed.add_field(name="Shard ID", value=guild.shard_id + 1)
        embed.set_footer(text=f"ID: {guild.id}")
        await self.bot.webhook.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not hasattr(self.bot, "uptime"):
            setattr(self.bot, "uptime", datetime.utcnow())

        log.info(f"Connected as {self.bot.user.display_name} in {len(self.bot.guilds)} guilds.")
        await self.send_log("Bot is online.", discord.Color.blue())

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        query = """INSERT INTO server (id)
                   VALUES ($1)
                   ON CONFLICT (id) DO NOTHING;
                """
        await self.bot.pool.execute(query, guild.id)

        if self.bot.debug:
            return

        embed = discord.Embed(color=discord.Color.green())
        await self.send_guild_log(guild, embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        await self.bot.pool.execute("DELETE FROM server WHERE id = $1;", guild.id)

        if self.bot.debug:
            return

        embed = discord.Embed(color=discord.Color.red())
        await self.send_guild_log(guild, embed)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if not self.bot.is_ready():
            return

        if interaction.type is discord.InteractionType.application_command:
            query = """INSERT INTO member (id)
                       VALUES ($1)
                       ON CONFLICT (id) DO NOTHING;
                    """
            await self.bot.pool.execute(query, interaction.user.id)

            if interaction.guild is not None:
                query = """INSERT INTO server (id)
                           VALUES ($1)
                           ON CONFLICT (id) DO NOTHING;
                        """
                await self.bot.pool.execute(query, interaction.guild_id)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        if not isinstance(channel, discord.TextChannel):
            return

        newsboard = await self.bot.get_cog("Overwatch").get_newsboard(channel.guild.id)
        if newsboard.channel_id != channel.id:
            return

        async with self.bot.pool.acquire(timeout=300.0) as conn:
            query = "DELETE FROM newsboard WHERE id = $1;"
            await conn.execute(query, channel.id)


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Events(bot))
