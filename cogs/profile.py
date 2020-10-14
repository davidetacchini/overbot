import asyncio

import discord
from discord.ext import commands

from utils.checks import has_profile, has_no_profile
from utils.globals import group_embed, profile_info, embed_exception
from classes.converters import Hero, Platform, Username

from .stats import Statistics


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def profile(self, ctx, command: str = None):
        """Displays a list with all its subcommands."""
        embed = group_embed(ctx, self.bot.get_command(ctx.command.name))
        await ctx.send(embed=embed)

    async def get_platform(self, ctx, msg):
        reactions = [
            "<:battlenet:679469162724196387>",
            "<:psn:679468542541693128>",
            "<:xbl:679469487623503930>",
            "<:nsw:752653766377078817>",
            "❌",
        ]

        for r in reactions:
            await msg.add_reaction(r)

        def check(r, u):
            return (
                u == ctx.author and str(r.emoji) in reactions and r.message.id == msg.id
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

        if str(reaction.emoji) == "<:battlenet:679469162724196387>":
            return "pc"
        elif str(reaction.emoji) == "<:psn:679468542541693128>":
            return "psn"
        elif str(reaction.emoji) == "<:xbl:679469487623503930>":
            return "xbl"
        elif str(reaction.emoji) == "<:nsw:752653766377078817>":
            return "nintendo-switch"
        return

    @has_no_profile()
    @profile.command(aliases=["bind"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def link(self, ctx):
        """Link your Overwatch profile to your Discord account."""
        embed = discord.Embed(color=self.bot.color)
        embed.title = "Link your Overwatch profile to your Discord ID"
        embed.description = "React with the platform you play on"
        embed.add_field(
            name="Platforms",
            value=(
                "<:battlenet:679469162724196387> - PC\n"
                "<:psn:679468542541693128> - PS4\n"
                "<:xbl:679469487623503930> - XBOX ONE\n"
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
                await ctx.send(embed=embed_exception(exc))
            else:
                await ctx.send(
                    f"Profile successfully linked. Run `{ctx.prefix}profile info` to see your profile information."
                )

    @has_profile()
    @profile.command(aliases=["unbind"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def unlink(self, ctx):
        """Unlink your Overwatch profile from your Discord account."""
        if not await ctx.confirm(
            f"Are you sure you want to unlink your Overwatch profile from your Discord account? You can always add a new one by running `{ctx.prefix}profile link`."
        ):
            return

        try:
            await self.bot.pool.execute(
                "DELETE FROM profile WHERE id=$1;", ctx.author.id
            )
            return await ctx.send("Profile successfully unlinked.")
        except Exception as exc:
            await ctx.send(embed=embed_exception(exc))

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def update(self, ctx, platform: Platform, *, username: Username):
        """Update your Overwatch profile linked to your Discord account."""
        try:
            await self.bot.pool.execute(
                'UPDATE profile SET "platform"=$1, "name"=$2 WHERE id=$3;',
                platform,
                username,
                ctx.author.id,
            )
        except Exception as exc:
            await ctx.send(embed=embed_exception(exc))
        else:
            await ctx.send(
                f"Profile successfully updated. Run `{ctx.prefix}profile info` to see the changes."
            )

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def info(self, ctx):
        """Displays your linked profile information."""
        try:
            profile = await self.bot.pool.fetchrow(
                "SELECT * FROM profile WHERE id=$1;", ctx.author.id
            )
            embed = profile_info(
                ctx, profile["platform"], profile["name"].replace("-", "#")
            )
            await ctx.send(embed=embed)
        except TypeError:
            await ctx.send(
                f"Connect your profile by running `{ctx.prefix}profile link`"
            )
        except Exception as exc:
            await ctx.send(embed=embed_exception(exc))

    async def embed_profile_stats(self, ctx, user_id, hero=None):
        """Embeds stats for commands."""
        try:
            profile = await self.bot.pool.fetchrow(
                "SELECT platform, name FROM profile WHERE id=$1;", user_id
            )
            await Statistics.embed_stats(
                ctx, profile["platform"], profile["name"], hero
            )
        except Exception as exc:
            await ctx.send(embed=embed_exception(exc))

    @has_profile()
    @profile.command(aliases=["rating"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rank(self, ctx, user: discord.Member = None):
        """Returns linked profile rank."""
        async with ctx.typing():
            user = user or ctx.author
            if not await self.bot.pool.fetchrow(
                "SELECT platform, name FROM profile WHERE id=$1", user.id
            ):
                return await ctx.send(f"{user} hasn't connected a profile yet.")
            await self.embed_profile_stats(ctx, user.id)

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def stats(self, ctx, user: discord.Member = None):
        """Returns linked profile both competitive and quick play statistics."""
        async with ctx.typing():
            user = user or ctx.author
            if not await self.bot.pool.fetchrow(
                "SELECT platform, name FROM profile WHERE id=$1", user.id
            ):
                return await ctx.send(f"{user} hasn't connected a profile yet.")
            await self.embed_profile_stats(ctx, user.id)

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def hero(self, ctx, hero: Hero, user: discord.Member = None):
        """Returns linked profile statistics for a given hero."""
        async with ctx.typing():
            user = user or ctx.author
            if not await self.bot.pool.fetchrow(
                "SELECT platform, name FROM profile WHERE id=$1", user.id
            ):
                return await ctx.send(f"{user} hasn't connected a profile yet.")
            await self.embed_profile_stats(ctx, user.id, hero)


def setup(bot):
    bot.add_cog(Profile(bot))
