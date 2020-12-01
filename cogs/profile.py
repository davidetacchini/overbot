import asyncio

import discord
from discord.ext import commands

from utils.data import RequestError
from utils.checks import has_profile, has_no_profile
from utils.player import Player, NoStatistics, NoHeroStatistics
from utils.paginator import Link
from classes.converters import Hero, Platform


class MemberHasNoProfile(Exception):
    """Exception raised when mentioned member has no profile connected."""

    def __init__(self, member):
        super().__init__(f"{member} hasn't linked a profile yet.")


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.platforms = {
            "pc": {
                "emoji": "<:battlenet:679469162724196387>",
                "color": discord.Color.blue(),
                "format": "Battletag",
            },
            "psn": {
                "emoji": "<:psn:679468542541693128>",
                "color": discord.Color.blue(),
                "format": "Online ID",
            },
            "xbl": {
                "emoji": "<:xbl:679469487623503930>",
                "color": discord.Color.green(),
                "format": "Gamertag",
            },
            "nintendo-switch": {
                "emoji": "<:nsw:752653766377078817>",
                "color": discord.Color.red(),
                "format": "Nintendo Switch ID",
            },
        }

    @commands.group(invoke_without_command=True)
    async def profile(self, ctx, command: str = None):
        """Displays a list with all profile's subcommands."""
        embed = self.bot.get_subcommands(ctx, ctx.command)
        await ctx.send(embed=embed)

    async def insert_or_update_profile(self, member_id, platform, username):
        username = str(username).replace("#", "-")
        await self.bot.pool.execute(
            "INSERT INTO profile(id, platform, name) VALUES($1, $2, $3) "
            "ON CONFLICT (id) DO UPDATE SET platform = $2, name = $3;",
            member_id,
            platform,
            username,
        )

    @has_no_profile()
    @profile.command(aliases=["bind"])
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    async def link(self, ctx):
        """Link your Overwatch profile to your Discord account."""
        title = "Link your Overwatch profile to your Discord ID"
        footer = "React with the platform you play on."
        platform = await Link(title=title, footer=footer).paginate(ctx)

        if not platform:
            return

        if platform == "pc":
            await ctx.send("Enter your battletag (in the following format: name#0000):")
        elif platform == "psn":
            await ctx.send("Enter your PSN ID:")
        elif platform == "xbl":
            await ctx.send("Enter your XBOX gamertag:")
        elif platform == "nintendo-switch":
            await ctx.send("Enter your Nintendo Switch ID:")
        else:
            return

        def check(m):
            if m.author.id != ctx.author.id:
                return False
            if m.channel.id != ctx.channel.id:
                return False
            return True

        try:
            username = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("You took too long to reply.")
        else:
            try:
                await self.insert_or_update_profile(
                    ctx.author.id, platform, username.content
                )
            except Exception as exc:
                await ctx.send(embed=self.bot.embed_exception(exc))
            else:
                await ctx.send(
                    f'Profile successfully linked. Use "{ctx.prefix}profile info" to see your profile information.'
                )

    @has_profile()
    @profile.command(aliases=["unbind"])
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    async def unlink(self, ctx):
        """Unlink your Overwatch profile from your Discord account."""
        if not await ctx.prompt(
            "Are you sure you want to unlink your Overwatch profile from your Discord account?"
        ):
            return

        try:
            await self.bot.pool.execute(
                "DELETE FROM profile WHERE id = $1;", ctx.author.id
            )
            return await ctx.send("Profile successfully unlinked.")
        except Exception as exc:
            await ctx.send(embed=self.bot.embed_exception(exc))

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    async def update(self, ctx, platform: Platform, *, username):
        """Update your Overwatch profile linked to your Discord account."""
        try:
            await self.insert_or_update_profile(ctx.author.id, platform, username)
        except Exception as exc:
            await ctx.send(embed=self.bot.embed_exception(exc))
        else:
            await ctx.send(
                f'Profile successfully updated. Use "{ctx.prefix}profile info" to see the changes.'
            )

    def profile_info(self, ctx, platform, name):
        """Returns linked profile information."""
        emoji = self.platforms.get(platform).get("emoji")
        color = self.platforms.get(platform).get("color")
        _format = self.platforms.get(platform).get("format")
        embed = discord.Embed(color=color)
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        embed.add_field(name="Platform", value=f"{emoji} {platform}")
        embed.add_field(name=_format, value=name)
        return embed

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    async def info(self, ctx):
        """Displays your linked profile information."""
        try:
            profile = await self.bot.pool.fetchrow(
                "SELECT platform, name FROM profile WHERE id = $1;", ctx.author.id
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

    async def get_profile(self, member):
        """Returns profile information."""
        profile = await self.bot.pool.fetchrow(
            "SELECT platform, name FROM profile WHERE id = $1;", member.id
        )
        if not profile:
            raise MemberHasNoProfile(member)
        return profile

    @has_profile()
    @profile.command(aliases=["rating"])
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    async def rank(self, ctx, member: discord.Member = None):
        """Shows a member's Overwatch ranks.

        `[member]` - The mention or the ID of a discord member of the current server.

        If no member is given then the ranks returned will be yours.
        """
        async with ctx.typing():
            member = member or ctx.author
            try:
                profile = await self.get_profile(member)
            except MemberHasNoProfile as exc:
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
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    async def statistics(self, ctx, member: discord.Member = None):
        """Shows a member's Overwatch both quick play and competitive statistics.

        `[member]` - The mention or the ID of a discord member of the current server.

        If no member is given then the statistics returned will be yours.
        """
        async with ctx.typing():
            member = member or ctx.author
            try:
                profile = await self.get_profile(member)
            except MemberHasNoProfile as exc:
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
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    async def hero(self, ctx, hero: Hero, member: discord.Member = None):
        """Shows a member's Overwatch both quick play and competitive statistics for a given hero.

        `<hero>` - The name of the hero you want to see stats for.
        `[member]` - The mention or the ID of a discord member of the current server.

        If no member is given then the statistics returned will be yours.
        """
        async with ctx.typing():
            member = member or ctx.author
            try:
                profile = await self.get_profile(member)
            except MemberHasNoProfile as exc:
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
