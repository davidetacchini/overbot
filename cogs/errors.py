import discord
from asyncpg import DataError
from discord.ext import commands

from utils import checks
from classes.context import NoChoice


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error, bypass=False):

        if (
            hasattr(ctx.command, "on_error")
            or (ctx.command and hasattr(ctx.cog, f"_{ctx.command.cog_name}__error"))
            and not bypass
        ):
            # return if a command has its own error handler
            return

        if isinstance(error, commands.CommandNotFound):
            return

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"You are missing a required argument: `{error.param.name}`")

        elif isinstance(error, commands.BadArgument):
            # print the message if given else printing the standard one
            await ctx.send(error or "You are using a bad argument.")

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have enough permissions.")

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                "You can't use `{command}` command for `{seconds}` seconds.".format(
                    command=ctx.command.name, seconds=round(error.retry_after, 2)
                )
            )

        elif isinstance(error, commands.NotOwner):
            await ctx.send("It seems you do not own this bot.")

        elif hasattr(error, "original") and isinstance(
            error.original, discord.HTTPException
        ):
            return

        elif isinstance(error, commands.CommandInvokeError) and hasattr(
            error, "original"
        ):
            if isinstance(error.original, DataError):
                await ctx.send("The argument you entered cannot be handled.")

        elif isinstance(error, commands.CheckFailure):
            if type(error) == checks.ProfileNotLinked:
                await ctx.send(
                    f"You must have linked a profile in order to access this command. Please run `{ctx.prefix}profile link` to do so."
                )

            elif type(error) == checks.ProfileAlreadyLinked:
                await ctx.send(
                    f"You have already linked a profile. Head to `{ctx.prefix}profile info` to see its information."
                )

            elif type(error) == checks.UserIsNotDonator:
                await ctx.send(
                    "Become a patron and unlock the pro features!"
                    f"\nMore information at {self.bot.config.patreon}"
                )

        elif isinstance(error, NoChoice):
            await ctx.send("You didn't choose anything.")


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
