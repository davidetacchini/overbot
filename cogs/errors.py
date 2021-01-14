import discord
from asyncpg import DataError
from discord.ext import commands
from discord.ext.menus import MenuError

from utils import checks
from utils.i18n import _, locale
from utils.paginator import NoChoice


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @locale
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):

        if hasattr(ctx.command, "on_error") or (
            ctx.command and hasattr(ctx.cog, f"_{ctx.command.cog_name}__error")
        ):
            # return if a command has its own error handler
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
            # print the message if given else printing the standard one
            await ctx.send(error or _("You are using a bad argument."))

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(_("You don't have enough permissions."))

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                _("You can't use `{command}` command for `{seconds}` seconds.").format(
                    command=ctx.command.qualified_name,
                    seconds=round(error.retry_after, 2),
                )
            )

        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send(_("This command can't be used in direct messages."))

        elif isinstance(error, commands.NotOwner):
            await ctx.send(_("It seems you do not own this bot."))

        elif hasattr(error, "original") and isinstance(error, MenuError):
            return

        elif hasattr(error, "original") and isinstance(
            error.original, discord.HTTPException
        ):
            return

        if isinstance(error, NoChoice):
            await ctx.send(_("You took too long to reply."))

        elif isinstance(error, commands.CommandInvokeError) and hasattr(
            error, "original"
        ):
            if isinstance(error.original, DataError):
                await ctx.send(_("The argument you entered cannot be handled."))

        elif isinstance(error, commands.CheckFailure):
            if type(error) == checks.ProfileNotLinked:
                await ctx.send(
                    _(
                        'You haven\'t linked a profile yet. Use "{prefix}profile link" to do so.'
                    ).format(prefix=ctx.prefix)
                )

            elif type(error) == checks.ProfileLimitReached:
                await ctx.send(
                    _(
                        'You have reached the maximum number of profiles that can be added. Use "{prefix}profile list" for more info.'
                    ).format(prefix=ctx.prefix)
                )


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
