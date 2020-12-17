from discord.ext import commands


class ProfileAlreadyLinked(commands.CheckFailure):
    """Exception raised when a user has already linked a profile."""

    pass


class ProfileNotLinked(commands.CheckFailure):
    """Exception raised when a user have not linked a profile."""

    pass


async def get_profile(ctx):
    query = """SELECT platform, username
            FROM profile
            INNER JOIN member
                    ON member.id = profile.member_id
            WHERE member.id = $1
            """
    return await ctx.bot.pool.fetchrow(query, ctx.author.id)


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
