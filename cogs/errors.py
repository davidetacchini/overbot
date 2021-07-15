import textwrap
import traceback

import discord

from asyncpg import DataError
from discord.ext import commands
from discord.ext.menus import MenuError

from utils import checks
from utils.i18n import _, locale
from classes.player import PlayerException
from classes.request import RequestError
from classes.exceptions import NoChoice


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @locale
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if ctx.command and ctx.command.has_error_handler():
            return

        if ctx.cog and ctx.cog.has_error_handler():
            return

        if isinstance(error, commands.CommandNotFound):
            return

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                _("You are missing a required argument: `{argument}`").format(
                    argument=error.param.name
                )
            )

        elif isinstance(error, commands.BadArgument):
            await ctx.send(error or _("You are using a bad argument."))

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(_("You don't have enough permissions."))

        elif isinstance(error, checks.MemberOnCooldown):
            await ctx.send(
                _(
                    "You are on cooldown. Wait `{seconds}s` before running another command."
                ).format(seconds=round(error.retry_after, 2))
            )

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                _("You can't use `{command}` command for `{seconds}s`.").format(
                    command=ctx.command.qualified_name,
                    seconds=round(error.retry_after, 2),
                )
            )

        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send(_("This command can't be used in direct messages."))

        elif isinstance(error, commands.NotOwner):
            await ctx.send(_("It seems you do not own this bot."))

        elif isinstance(error, commands.CheckFailure):
            if type(error) == checks.ProfileNotLinked:
                await ctx.send(
                    _(
                        'You haven\'t linked a profile yet. Use "{prefix}profile link" to start.'
                    ).format(prefix=ctx.prefix)
                )

            elif type(error) == checks.ProfileLimitReached:
                if error.limit == 5:
                    embed = discord.Embed(color=discord.Color.red())
                    embed.description = _(
                        "Max profiles limit reached.\n[Upgrade to Premium]({premium}) to be able to link up to 25 profiles."
                    ).format(premium=self.bot.config.premium)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(_("Max profiles limit reached."))

            elif type(error) == checks.MemberIsNotPremium:
                embed = discord.Embed(color=discord.Color.red())
                embed.description = _(
                    "This command requires a Premium membership.\n[Click here]({premium}) to have a look at the Premium plan.".format(
                        premium=self.bot.config.premium
                    )
                )
                await ctx.send(embed=embed)

        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            group = (RequestError, PlayerException, NoChoice, MenuError)
            if isinstance(original, discord.HTTPException):
                return
            elif isinstance(original, DataError):
                await ctx.send(_("The argument you entered cannot be handled."))
            elif isinstance(original, group):
                await ctx.send(original)
            else:
                embed = discord.Embed(color=discord.Color.red())
                embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
                embed.add_field(name="Command", value=ctx.command.qualified_name)
                content = textwrap.shorten(ctx.message.content, width=512)
                embed.add_field(name="Content", value=content)
                if ctx.guild:
                    guild = f"{str(ctx.guild)} ({ctx.guild.id})"
                    embed.add_field(name="Guild", value=guild, inline=False)
                try:
                    exc = "".join(
                        traceback.format_exception(
                            type(original),
                            original,
                            original.__traceback__,
                            chain=False,
                        )
                    )
                except AttributeError:
                    exc = f"{type(original)}\n{original}"
                embed.description = f"```py\n{exc}\n```"
                embed.timestamp = ctx.message.created_at
                if not self.bot.debug:
                    await self.bot.webhook.send(embed=embed)
                else:
                    print(original, type(original))
                await ctx.send(
                    _(
                        "This command ran into an error. The incident has been reported and will be fixed as soon as possible!"
                    )
                )


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
