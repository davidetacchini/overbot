import discord
from discord.ext import commands


class ProfileAlreadyLinked(commands.CheckFailure):
    """Exception raised when a user has already linked a profile."""

    pass


class ProfileNotLinked(commands.CheckFailure):
    """Exception raised when a user have not linked a profile."""

    pass


class UserIsNotDonator(commands.CheckFailure):
    """Exception raised when a user is not a donator."""

    pass


def is_donator():
    """Check for a user to be a patreon member."""

    async def predicate(ctx):
        guild = ctx.bot.get_guild(ctx.bot.config.support_server_id)
        member = await guild.fetch_member(ctx.author.id)

        if not member:
            return False

        role = (
            discord.utils.get(member.roles, name="Sith") is not None
            or discord.utils.get(member.roles, name="Jedi") is not None
            or discord.utils.get(member.roles, name="Galaxy Lord") is not None
            or discord.utils.get(member.roles, name="Admin") is not None
        )

        if role:
            return True
        raise UserIsNotDonator()

    return commands.check(predicate)


async def get_profile(ctx):
    return await ctx.bot.pool.fetchrow(
        "SELECT platform, name FROM profile WHERE id=$1;", ctx.author.id
    )


def has_profile():
    """Check for a user to have linked a profile."""

    async def predicate(ctx):
        if await get_profile(ctx):
            return True
        raise ProfileNotLinked()

    return commands.check(predicate)


def has_no_profile():
    """Check for a user to have no profile linked."""

    async def predicate(ctx):
        if not await get_profile(ctx):
            return True
        raise ProfileAlreadyLinked()

    return commands.check(predicate)
