from typing import Union, Optional

import discord
from discord.ext import commands

from utils.checks import is_donator
from utils.globals import embed_exception, command_signature


class Server(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_settings_status(self, ctx):
        guild = await self.bot.pool.fetchrow(
            'SELECT "prefix", news_channel FROM server WHERE id=$1;', ctx.guild.id
        )
        c = self.bot.get_channel(guild["news_channel"])
        return {
            "news": f"<:online:648186001361076243> `Enabled` in **{str(c) if c.id != ctx.channel.id else 'this channel'}**"
            if guild["news_channel"] != 0
            else "<:dnd:648185968209428490> `Disabled`",
            "prefix": f"Current prefix set: `{guild['prefix']}`",
        }

    async def embed_settings(self, ctx, command):
        subcommands = getattr(command, "commands", None)
        setting = await self.get_settings_status(ctx)

        embed = discord.Embed(color=self.bot.color)
        embed.title = f"{ctx.guild.name}'s settings for OverBot"
        embed.description = (
            f"You can use `{ctx.prefix}settings [setting] [value]` to change the value of a specific setting."
            f" For example, `{ctx.prefix}settings news enable`."
            f" Settings can be reset by running `{ctx.prefix}settings reset`."
        )
        for subcommand in subcommands:
            if subcommand.callback.__doc__:
                desc = subcommand.callback.__doc__
            else:
                desc = "No description set"
            if subcommand.name == "reset":
                continue
            try:
                embed.add_field(
                    name=command_signature(subcommand),
                    value=f"{desc}\n{setting[subcommand.name]}",
                    inline=False,
                )
            except KeyError:
                embed.add_field(
                    name=command_signature(subcommand),
                    value=desc,
                )
        return embed

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def settings(self, ctx, command: str = None):
        """Change the settings for your Discord server."""
        embed = await self.embed_settings(ctx, self.bot.get_command(ctx.command.name))
        await ctx.send(embed=embed)

    @settings.command(name="prefix")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def _prefix(self, ctx, prefix):
        """Change the prefix for this server."""
        if len(prefix) > 5:
            return await ctx.send("Prefixes may not be longer than 5 characters.")

        try:
            await self.bot.pool.execute(
                'UPDATE server SET "prefix"=$1 WHERE id=$2;', prefix, ctx.guild.id
            )
        except Exception as exc:
            await ctx.send(embed=embed_exception(exc))
        else:
            await ctx.send(f"Prefix successfully set to `{prefix}`")

    @settings.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def reset(self, ctx):
        """Reset the server settings."""
        if not await ctx.confirm(
            "Are you sure you want to reset this server settings?"
        ):
            return

        await self.bot.pool.execute(
            'UPDATE server SET "prefix"=$1, news_channel=0 WHERE id=$2;',
            self.bot.config.default_prefix,
            ctx.guild.id,
        )
        await ctx.send("Settings have been successfully reset.")

    @is_donator()
    @settings.command(brief="premium")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def news(
        self,
        ctx,
        choice: str,
        channel: Optional[Union[int, discord.TextChannel]] = None,
    ):
        """Set up live Overwatch news feed to a channel. If no channel is provided, the channel ID in which this command is executed is used."""
        choice = choice.lower()
        channel = channel or ctx.channel.id
        if isinstance(channel, int):
            ch = self.bot.get_channel(channel)
        else:
            ch = channel

        if ch not in [c for c in ctx.guild.channels]:
            return await ctx.send("The channel ID must be from this server.")

        if not isinstance(ch, discord.TextChannel):
            return await ctx.send("The news channel must be a text one.")

        if not ch.permissions_for(ctx.guild.me).send_messages:
            return await ctx.send(
                f"I can't send messages in that channel. Please provide a channel where I can send messages to, or give me `Send Messages` permission in **{str(ch)}**."
            )

        if choice == "enable":
            await self.bot.pool.execute(
                "UPDATE server SET news_channel=$1 WHERE id=$2;",
                ch.id,
                ctx.guild.id,
            )
            channel_name = str(ch) if ch.id != ctx.channel.id else "this channel"
            return await ctx.send(
                f"You have enabled news notification in **{channel_name}**. To disable this setting run: `{ctx.prefix}settings news disable`"
            )
        elif choice == "disable":
            await self.bot.pool.execute(
                "UPDATE server SET news_channel=0 WHERE id=$1;", ctx.guild.id
            )
            return await ctx.send("You won't receive news notification anymore.")
        raise commands.BadArgument(
            "Bad argument! This setting only accepts `enable/disable`"
        )

    @commands.command()
    @commands.guild_only()
    async def prefix(self, ctx):
        """Displays information about the prefix."""
        _prefix = await self.bot.pool.fetchval(
            "SELECT prefix FROM server WHERE id=$1;", ctx.guild.id
        )
        embed = discord.Embed(title="Prefix Information", color=self.bot.color)
        embed.add_field(name="Current prefix", value=f"`{_prefix}`")
        embed.add_field(
            name="Want to change it?", value=f"`{_prefix}settings prefix <prefix>`"
        )
        embed.add_field(
            name="Permissions",
            value="`Manage Server` permission is required to change the prefix.",
            inline=False,
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Server(bot))
