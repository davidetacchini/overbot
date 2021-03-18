import discord
from discord.ext import commands


class ProfileNotLinked(commands.CheckFailure):
    """Exception raised when a user have not linked a profile."""

    pass


class ProfileLimitReached(commands.CheckFailure):
    """Exception raised when a user try to link a 6th profile."""

    def __init__(self, limit):
        self.limit = limit


class MemberIsNotPremium(commands.CheckFailure):
    """Exception raised when a user is not premium."""

    pass


class MemberOnCooldown(commands.CommandOnCooldown):
    """Exception raised when a user is on cooldown (globally)."""

    pass


async def global_cooldown(ctx):
    if not await member_is_premium(ctx):
        bucket = ctx.bot.normal_cooldown.get_bucket(ctx.message)
    else:
        bucket = ctx.bot.premium_cooldown.get_bucket(ctx.message)

    retry_after = bucket.update_rate_limit()

    if retry_after:
        raise MemberOnCooldown(bucket, retry_after)
    else:
        return True


async def get_profiles(ctx):
    query = """SELECT platform, username
            FROM profile
            INNER JOIN member
                    ON member.id = profile.member_id
            WHERE member.id = $1;
            """
    return await ctx.bot.pool.fetch(query, ctx.author.id)


def has_profile():
    """Check for a user to have linked atleast a profile."""

    async def predicate(ctx):
        if await get_profiles(ctx):
            return True
        raise ProfileNotLinked()

    return commands.check(predicate)


def can_add_profile():
    """Check for a user to have no profiles linked."""

    async def predicate(ctx):
        profiles = await get_profiles(ctx)

        if not await member_is_premium(ctx):
            limit = 5
        else:
            limit = 25

        if len(profiles) < limit:
            return True
        raise ProfileLimitReached(limit)

    return commands.check(predicate)


async def member_is_premium(ctx):
    """Check for a user to be a premium member."""
    guild = ctx.bot.get_guild(ctx.bot.config.support_server_id)

    try:
        member = await guild.fetch_member(ctx.author.id)
    except discord.HTTPException:
        return False

    role = discord.utils.get(member.roles, name="Premium")

    if role:
        return True
    return False


def is_premium():
    """Check for a user to be a premium member."""

    async def predicate(ctx):
        guild = ctx.bot.get_guild(ctx.bot.config.support_server_id)

        try:
            member = await guild.fetch_member(ctx.author.id)
        except discord.HTTPException:
            raise MemberIsNotPremium()

        role = discord.utils.get(member.roles, name="Premium")

        if role:
            return True
        raise MemberIsNotPremium()

    return commands.check(predicate)
