import asyncio

import discord
from discord.ext import commands

from utils.data import RequestError
from utils.checks import has_profile, has_no_profile
from utils.player import Player, NoStatistics, NoHeroStatistics
from classes.converters import Hero, Platform

PLATFORMS = {
    "pc": ("<:battlenet:679469162724196387>", discord.Color.blue()),
    "psn": ("<:psn:679468542541693128>", discord.Color.blue()),
    "xbl": ("<:xbl:679469487623503930>", discord.Color.green()),
    "nintendo-switch": ("<:nsw:752653766377078817>", discord.Color.red()),
}


class UserHasNoProfile(Exception):
    """Exception raised when tagged user has no profile connected."""

    def __init__(self, username):
        message = f"{username} hasn't linked a profile yet."
        super().__init__(message)


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reactions = {
            "<:battlenet:679469162724196387>": "pc",
            "<:psn:679468542541693128>": "psn",
            "<:xbl:679469487623503930>": "xbl",
            "<:nsw:752653766377078817>": "nintendo-switch",
            "❌": "close",
        }

    async def add_reactions(self, msg):
        for r in self.reactions:
            await msg.add_reaction(r)

    async def get_platform(self, ctx, msg):
        self.bot.loop.create_task(self.add_reactions(msg))

        def check(r, u):
            return (
                u == ctx.author
                and str(r.emoji) in self.reactions
                and r.message.id == msg.id
            )

        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", check=check, timeout=30
            )
            await msg.delete()
        except asyncio.TimeoutError:
            await ctx.send("You didn't choose any platform.")
            return
            # return to avoid displaying an UnboundLocalError if no choice is given

        return self.reactions.get(str(reaction.emoji))

    @commands.group(invoke_without_command=True)
    async def profile(self, ctx, command: str = None):
        """Displays a list with all profile's subcommands."""
        embed = self.bot.get_subcommands(ctx, self.bot.get_command(ctx.command.name))
        await ctx.send(embed=embed)

    @has_no_profile()
    @profile.command(aliases=["bind"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def link(self, ctx):
        """Link your Overwatch profile to your Discord account."""
        embed = discord.Embed(color=self.bot.color)
        embed.title = "Link your Overwatch profile to your Discord ID"
        embed.description = "React with the platform you play on"
        embed.add_field(
            name="Platforms",
            value=(
                "<:battlenet:679469162724196387> - PC\n"
                "<:psn:679468542541693128> - PS\n"
                "<:xbl:679469487623503930> - XBOX\n"
                "<:nsw:752653766377078817> - NINTENDO SWITCH"
            ),
        )
        msg = await ctx.send(embed=embed, delete_after=30)
        platform = await self.get_platform(ctx, msg)

        if not platform:
            return

        if platform == "pc":
            await ctx.send("Enter your battletag (in the following format: name#0000):")
        elif platform == "psn":
            await ctx.send("Enter your PSN ID:")
        elif platform == "xbl":
            await ctx.send("Enter your XBOX gamertag:")
        else:
            await ctx.send("Enter your Nintendo Switch ID:")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            username = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("You took too long to reply.")
        else:
            try:
                await self.bot.pool.execute(
                    'INSERT INTO profile (id, "platform", "name") VALUES ($1, $2, $3);',
                    ctx.author.id,
                    platform,
                    str(username.content).replace("#", "-"),
                )
            except Exception as exc:
                await ctx.send(embed=self.bot.embed_exception(exc))
            else:
                await ctx.send(
                    f'Profile successfully linked. Run "{ctx.prefix}profile info" to see your profile information.'
                )

    @has_profile()
    @profile.command(aliases=["unbind"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def unlink(self, ctx):
        """Unlink your Overwatch profile from your Discord account."""
        if not await ctx.prompt(
            "Are you sure you want to unlink your Overwatch profile from your Discord account?"
            f' You can always add a new one by running "{ctx.prefix}profile link".'
        ):
            return

        try:
            await self.bot.pool.execute(
                "DELETE FROM profile WHERE id=$1;", ctx.author.id
            )
            return await ctx.send("Profile successfully unlinked.")
        except Exception as exc:
            await ctx.send(embed=self.bot.embed_exception(exc))

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def update(self, ctx, platform: Platform, *, username):
        """Update your Overwatch profile linked to your Discord account."""
        try:
            await self.bot.pool.execute(
                'UPDATE profile SET "platform"=$1, "name"=$2 WHERE id=$3;',
                platform,
                username,
                ctx.author.id,
            )
        except Exception as exc:
            await ctx.send(embed=self.bot.embed_exception(exc))
        else:
            await ctx.send(
                f'Profile successfully updated. Run "{ctx.prefix}profile info" to see the changes.'
            )

    def resolved_platform_name(self, platform):
        if platform == "pc":
            return "Battletag"
        elif platform == "psn":
            return "Online ID"
        elif platform == "xbl":
            return "Gamertag"
        else:
            return "Nintendo Switch ID"

    def profile_info(self, ctx, platform, name):
        """Returns linked profile information."""
        embed = discord.Embed(color=PLATFORMS[platform][1])
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        embed.add_field(name="Platform", value=f"{PLATFORMS[platform][0]} {platform}")
        embed.add_field(name=self.resolved_platform_name(platform), value=name)
        return embed

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def info(self, ctx):
        """Displays your linked profile information."""
        try:
            profile = await self.bot.pool.fetchrow(
                "SELECT platform, name FROM profile WHERE id=$1;", ctx.author.id
            )
            if profile["platform"] == "pc":
                # Replace '-' with '#' only if the platform is PC. UI purpose only.
                name = profile["name"].replace("-", "#")
            else:
                name = profile["name"]
            embed = self.profile_info(ctx, profile["platform"], name)
        except Exception as exc:
            await ctx.send(embed=self.bot.embed_exception(exc))
        else:
            await ctx.send(embed=embed)

    async def get_profile(self, user):
        """Returns profile information."""
        profile = await self.bot.pool.fetchrow(
            "SELECT platform, name FROM profile WHERE id=$1", user.id
        )
        if profile:
            return profile
        else:
            raise UserHasNoProfile(user)

    @has_profile()
    @profile.command(aliases=["rating"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def rank(self, ctx, user: discord.Member = None):
        """Returns linked profile ranks.

        `[user]` - Must be a mention or the ID of a Discord member.

        If no user is passed, the profile of the author of the message will be used.
        """
        async with ctx.typing():
            user = user or ctx.author
            try:
                profile = await self.get_profile(user)
            except UserHasNoProfile as exc:
                await ctx.send(exc)
            else:
                try:
                    data = await self.bot.data.Data(
                        platform=profile["platform"], name=profile["name"]
                    ).get()
                except RequestError as exc:
                    await ctx.send(exc)
                except Exception as exc:
                    await ctx.send(embed=self.bot.embed_exception(exc))
                else:
                    try:
                        profile = Player(
                            data=data,
                            platform=profile["platform"],
                            name=profile["name"],
                        )
                        if profile.is_private:
                            embed = profile.private(ctx)
                        else:
                            embed = profile.rank()
                    except Exception as exc:
                        await ctx.send(exc)
                    else:
                        await self.bot.paginator.Paginator(pages=embed).paginate(ctx)

    @has_profile()
    @profile.command(aliases=["stats"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def statistics(self, ctx, user: discord.Member = None):
        """Returns linked profile both competitive and quick play statistics.

        `[user]` - Must be a mention or the ID of a Discord member.

        If no user is passed, the profile of the author of the message will be used.
        """
        async with ctx.typing():
            user = user or ctx.author
            try:
                profile = await self.get_profile(user)
            except UserHasNoProfile as exc:
                await ctx.send(exc)
            else:
                try:
                    data = await self.bot.data.Data(
                        platform=profile["platform"], name=profile["name"]
                    ).get()
                except RequestError as exc:
                    await ctx.send(exc)
                except Exception as exc:
                    await ctx.send(embed=self.bot.embed_exception(exc))
                else:
                    try:
                        profile = Player(
                            data=data,
                            platform=profile["platform"],
                            name=profile["name"],
                        )
                        if profile.is_private:
                            embed = profile.private(ctx)
                        else:
                            embed = profile.statistics(ctx)
                    except NoStatistics as exc:
                        await ctx.send(exc)
                    except Exception as exc:
                        await ctx.send(embed=self.bot.embed_exception(exc))
                    else:
                        await self.bot.paginator.Paginator(pages=embed).paginate(ctx)

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def hero(self, ctx, hero: Hero, user: discord.Member = None):
        """Returns linked profile statistics for a given hero.

        `<hero>` - The name of the hero you want to see stats for.
        `[user]` - Must be a mention or the ID of a Discord member.

        If no user is passed, the profile of the author of the message will be used.
        """
        async with ctx.typing():
            user = user or ctx.author
            try:
                profile = await self.get_profile(user)
            except UserHasNoProfile as exc:
                await ctx.send(exc)
            else:
                try:
                    data = await self.bot.data.Data(
                        platform=profile["platform"], name=profile["name"]
                    ).get()
                except RequestError as exc:
                    await ctx.send(exc)
                except Exception as exc:
                    await ctx.send(embed=self.bot.embed_exception(exc))
                else:
                    try:
                        profile = Player(
                            data=data,
                            platform=profile["platform"],
                            name=profile["name"],
                        )
                        if profile.is_private:
                            embed = profile.private(ctx)
                        else:
                            embed = profile.hero(ctx, hero)
                    except NoHeroStatistics as exc:
                        await ctx.send(exc)
                    except Exception as exc:
                        await ctx.send(embed=self.bot.embed_exception(exc))
                    else:
                        await self.bot.paginator.Paginator(pages=embed).paginate(ctx)


def setup(bot):
    bot.add_cog(Profile(bot))
