from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import Color, app_commands
from discord.ext import commands

import config
from classes.exceptions import InvalidColor
from utils.checks import is_premium

if TYPE_CHECKING:
    from bot import OverBot

Member = discord.User | discord.Member


class ColorTransformer(app_commands.Transformer):
    @classmethod
    async def transform(cls, interaction: discord.Interaction, value: str) -> discord.Color:
        if len(value.split(",")) == 3:
            r, g, b = value.split(",")
            value = f"rgb({r}, {g}, {b})"
        try:
            color = Color.from_str(value)
        except ValueError:
            raise InvalidColor() from None
        else:
            return color


class MemberCog(commands.Cog, name="member"):
    def __init__(self, bot: OverBot) -> None:
        self.bot = bot

    @app_commands.command()
    async def premium(self, interaction: discord.Interaction) -> None:
        """Shows your premium status."""
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.title = "Premium Status"

        member = "Premium" if interaction.user.id in self.bot.premiums else "N/A"
        guild = "Premium" if interaction.guild_id in self.bot.premiums else "N/A"

        embed.description = f"Your Status: `{member}`\nServer Status: `{guild}`"

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Premium", url=self.bot.config.premium))

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(extras=dict(premium=True))
    @app_commands.describe(
        color="An HEX or RGB color. E.g. #218ffe or 33,143,254. Leave blank to reset"
    )
    @is_premium()
    async def color(
        self,
        interaction: discord.Interaction,
        *,
        color: app_commands.Transform[str, ColorTransformer] = None,
    ) -> None:
        """Set a custom color for the embeds."""
        if color is None:
            query = "UPDATE member SET embed_color = NULL WHERE id = $1;"
            await self.bot.pool.execute(query, interaction.user.id)
            try:
                del self.bot.embed_colors[interaction.user.id]
            except KeyError:
                await interaction.response.send_message(
                    "Color already set to default.", ephemeral=True
                )
                return
            else:
                await interaction.response.send_message("Color successfully reset.", ephemeral=True)
                return

        assert isinstance(color, discord.Color)
        embed = discord.Embed(color=color)
        query = "UPDATE member SET embed_color = $1 WHERE id = $2;"
        await self.bot.pool.execute(query, color, interaction.user.id)
        self.bot.embed_colors[interaction.user.id] = int(color)
        embed.description = "Color successfully set."
        await interaction.response.send_message(embed=embed)

    @app_commands.command(extras=dict(premium=True))
    @app_commands.guilds(config.support_server_id)
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    @is_premium()
    async def premiumrole(self, interaction: discord.Interaction) -> None:
        """Unlock the premium role"""
        await interaction.response.defer(thinking=True)

        assert isinstance(interaction.user, discord.Member)

        premium_role_id = 818466886491701278
        premium_role = discord.Object(id=premium_role_id)

        if interaction.user.get_role(premium_role_id):
            await interaction.followup.send(
                f"You have already been assigned the <@&{premium_role_id}> role."
            )
            return
        elif interaction.user.id in self.bot.premiums:
            try:
                await interaction.user.add_roles(premium_role, reason="Premium user")
            except discord.HTTPException:
                await interaction.followup.send("Something bad happened.")
            else:
                await interaction.followup.send(f"<@&{premium_role_id}> role successfully set.")

    async def get_member_usage(self, member: Member) -> discord.Embed:
        embed = discord.Embed(color=self.bot.color(member_id=member.id))
        embed.title = "Command Usage"
        embed.set_author(name=str(member), icon_url=member.display_avatar)

        query = "SELECT COUNT(*), MIN(created_at) FROM command WHERE author_id = $1;"
        count, timestap = await self.bot.pool.fetchrow(query, member.id)

        embed.description = f"{count} commands used"
        embed.set_footer(text="First command used").timestamp = timestap

        query = """SELECT name, count(*) as total from command
                   WHERE author_id = $1
                   GROUP BY name
                   ORDER BY total DESC
                   LIMIT 5;
                """

        commands = await self.bot.pool.fetch(query, member.id)

        value = "\n".join(f"{i}. {c['name']} ({c['total']} uses)" for i, c in enumerate(commands))
        embed.add_field(name="Top Commands", value=value)

        query = """SELECT name, count(*) as total from command
                   WHERE author_id = $1
                   AND created_at > (CURRENT_TIMESTAMP - '1 week'::interval)
                   GROUP BY name
                   ORDER BY total DESC
                   LIMIT 5;
                """

        commands = await self.bot.pool.fetch(query, member.id)

        value = "\n".join(f"{i}. {c['name']} ({c['total']} uses)" for i, c in enumerate(commands))
        embed.add_field(name="Top Commands This Week", value=value)

        query = """SELECT name, count(*) as total from command
                   WHERE author_id = $1
                   AND created_at > (CURRENT_TIMESTAMP - '1 day'::interval)
                   GROUP BY name
                   ORDER BY total DESC
                   LIMIT 5;
                """

        commands = await self.bot.pool.fetch(query, member.id)

        value = "\n".join(f"{i}. {c['name']} ({c['total']} uses)" for i, c in enumerate(commands))
        embed.add_field(name="Top Commands Today", value=value)

        return embed

    async def get_guild_usage(self, guild: discord.Guild, *, member_id: int) -> discord.Embed:
        embed = discord.Embed(color=self.bot.color(member_id))
        embed.title = "Command Usage"
        embed.set_author(name=str(guild), icon_url=guild.icon)

        query = "SELECT COUNT(*), MIN(created_at) FROM command WHERE guild_id = $1;"
        count, timestap = await self.bot.pool.fetchrow(query, guild.id)

        embed.description = f"{count} commands used"
        embed.set_footer(text="First command used").timestamp = timestap

        query = """SELECT name, count(*) as total from command
                   WHERE guild_id = $1
                   GROUP BY name
                   ORDER BY total DESC
                   LIMIT 5;
                """
        commands = await self.bot.pool.fetch(query, guild.id)

        value = "\n".join(f"{i}. {c['name']} ({c['total']} uses)" for i, c in enumerate(commands))
        embed.add_field(name="Top Commands", value=value)

        query = """SELECT name, count(*) as total from command
                   WHERE guild_id = $1
                   AND created_at > (CURRENT_TIMESTAMP - '1 week'::interval)
                   GROUP BY name
                   ORDER BY total DESC
                   LIMIT 5;
                """

        commands = await self.bot.pool.fetch(query, guild.id)

        value = "\n".join(f"{i}. {c['name']} ({c['total']} uses)" for i, c in enumerate(commands))
        embed.add_field(name="Top Commands This week", value=value)

        query = """SELECT name, count(*) as total from command
                   WHERE guild_id = $1
                   AND created_at > (CURRENT_TIMESTAMP - '1 day'::interval)
                   GROUP BY name
                   ORDER BY total DESC
                   LIMIT 5;
                """

        commands = await self.bot.pool.fetch(query, guild.id)

        value = "\n".join(f"{i}. {c['name']} ({c['total']} uses)" for i, c in enumerate(commands))
        embed.add_field(name="Top Commands Today", value=value)

        query = """SELECT author_id, count(*) as total from command
                   WHERE guild_id = $1
                   AND created_at > (CURRENT_TIMESTAMP - '1 day'::interval)
                   GROUP BY author_id
                   ORDER BY total DESC
                   LIMIT 5;
                """

        commands = await self.bot.pool.fetch(query, guild.id)

        value = "\n".join(
            f"{i}. <@!{c['author_id']}> ({c['total']} uses)" for i, c in enumerate(commands)
        )
        embed.add_field(name="Top Members", value=value)

        return embed

    @app_commands.command(extras=dict(premium=True))
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    @app_commands.describe(member="The member to show trivia stats for")
    @is_premium()
    async def usage(self, interaction: discord.Interaction, member: None | Member = None) -> None:
        """Shows your and the current server's OverBot usage."""
        await interaction.response.defer(thinking=True)

        pages = []
        member = member or interaction.user

        embed = await self.get_member_usage(member)
        pages.append(embed)

        if interaction.guild:
            embed = await self.get_guild_usage(interaction.guild, member_id=member.id)
            pages.append(embed)

        await self.bot.paginate(pages, interaction=interaction)


async def setup(bot: OverBot) -> None:
    await bot.add_cog(MemberCog(bot))
