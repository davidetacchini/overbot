from discord.ext import commands


class ProfileNotLinked(commands.CheckFailure):

    pass


class ProfileLimitReached(commands.CheckFailure):
    def __init__(self, limit):
        self.limit = limit


class MemberIsNotPremium(commands.CheckFailure):

    pass


class MemberOnCooldown(commands.CommandOnCooldown):

    pass


async def global_cooldown(ctx):
    member_id = ctx.author.id
    guild_id = ctx.guild.id if ctx.guild is not None else 0

    if not ctx.bot.member_is_premium(member_id, guild_id):
        bucket = ctx.bot.normal_cooldown.get_bucket(ctx.message)
    else:
        bucket = ctx.bot.premium_cooldown.get_bucket(ctx.message)

    retry_after = bucket.update_rate_limit()
    type_ = commands.BucketType.member

    if retry_after:
        raise MemberOnCooldown(bucket, retry_after, type_)
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
        limit = ctx.bot.get_profiles_limit(ctx, ctx.author.id)

        if len(profiles) >= limit:
            raise ProfileLimitReached(limit)
        return True

    return commands.check(predicate)


def is_premium():
    """Check for a user/server to be premium."""

    async def predicate(ctx):
        member_id = ctx.author.id
        guild_id = ctx.guild.id if ctx.guild is not None else 0
        to_check = (member_id, guild_id)

        if all(x not in ctx.bot.premiums for x in to_check):
            raise MemberIsNotPremium()
        return True

    return commands.check(predicate)
