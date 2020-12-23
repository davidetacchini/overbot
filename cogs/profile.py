import asyncio

import discord
from discord.ext import commands

from utils.checks import has_profile, can_add_profile
from utils.player import Player, NoStatistics, NoHeroStatistics
from utils.request import Request, RequestError
from utils.paginator import Link, Update
from classes.converters import Hero, Index

ROLES = {
    "tank": "\N{SHIELD}",
    "damage": "\N{CROSSED SWORDS}",
    "support": "\N{HEAVY GREEK CROSS}",
}


class MemberHasNoProfile(Exception):
    """Exception raised when mentioned member has no profile connected."""

    def __init__(self, member):
        super().__init__(f"{member} hasn't linked a profile yet.")


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.platforms = {
            "pc": "<:battlenet:679469162724196387>",
            "psn": "<:psn:679468542541693128>",
            "xbl": "<:xbl:679469487623503930>",
            "nintendo-switch": "<:nsw:752653766377078817>",
        }

    async def get_profiles(self, member):
        query = """SELECT profile.id, platform, username
                FROM profile
                INNER JOIN member
                        ON member.id = profile.member_id
                WHERE member.id = $1;
                """
        profiles = await self.bot.pool.fetch(query, member.id)
        if not profiles:
            raise MemberHasNoProfile(member)
        return profiles

    async def get_profile(self, member, *, index):
        if index:
            profiles = await self.get_profiles(member)
            profile = profiles[abs(index) - 1]
        else:
            query = """SELECT profile.id, platform, username
                    FROM profile
                    INNER JOIN member
                            ON member.main_profile = profile.id
                    WHERE member.id = $1;
                    """
            profile = await self.bot.pool.fetchrow(query, member.id)
        if not profile:
            raise MemberHasNoProfile(member)
        return profile

    async def set_main_profile(self, member_id, profile_id):
        query = "UPDATE member SET main_profile = $1 WHERE id = $2;"
        await self.bot.pool.execute(query, profile_id, member_id)

    async def is_main_profile(self, member_id, profile_id):
        query = "SELECT main_profile FROM member WHERE id = $1;"
        return await self.bot.pool.fetchval(query, member_id) == profile_id

    async def has_main_profile(self, member_id):
        query = "SELECT main_profile FROM member WHERE id = $1"
        if await self.bot.pool.fetchval(query, member_id):
            return True
        return False

    async def insert_profile(self, platform, username, *, member_id):
        query = "INSERT INTO profile(platform, username, member_id) VALUES($1, $2, $3);"
        await self.bot.pool.execute(query, platform, username, member_id)

    async def update_profile(self, platform, username, *, profile_id):
        query = "UPDATE profile SET platform = $1, username = $2 WHERE id = $3;"
        await self.bot.pool.execute(query, platform, username, profile_id)

    async def list_profiles(self, profiles, member):
        embed = discord.Embed(color=member.color)
        embed.set_author(name=str(member), icon_url=member.avatar_url)
        embed.set_footer(
            text=f"The star indicates the main profile - {len(profiles)}/5"
        )
        description = []
        for index, (id, platform, username) in enumerate(profiles, start=1):
            if platform == "pc":
                username = username.replace("-", "#")
            if not await self.is_main_profile(member.id, id):
                fmt = f"{index}. {platform} - {username}"
            else:
                fmt = f"{index}. {platform} - {username} :star:"
            description.append(fmt)
        embed.description = "\n".join(description)
        return embed

    async def get_player_username(self, ctx, platform):
        if platform == "pc":
            await ctx.send("Enter your BattleTag (format: name#0000):")
        elif platform == "psn":
            await ctx.send("Enter your Online ID:")
        elif platform == "xbl":
            await ctx.send("Enter your Gamertag:")
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
            message = await self.bot.wait_for("message", check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("You took too long to reply.")
        else:
            return message.content.replace("#", "-")

    @commands.group(invoke_without_command=True)
    @commands.cooldown(1, 1.0, commands.BucketType.member)
    async def profile(self, ctx, command: str = None):
        """Displays a list with all profile's subcommands."""
        embed = self.bot.get_subcommands(ctx, ctx.command)
        await ctx.send(embed=embed)

    @can_add_profile()
    @profile.command(aliases=["add", "bind"])
    @commands.cooldown(1, 3.0, commands.BucketType.member)
    async def link(self, ctx):
        """Link your Overwatch profile(s) to your Discord account."""
        title = "Link your Overwatch profile to your Discord ID"
        platform = await Link(title=title).start(ctx)
        username = await self.get_player_username(ctx, platform)
        if not username:
            return
        try:
            await self.insert_profile(platform, username, member_id=ctx.author.id)
            if not await self.has_main_profile(ctx.author.id):
                # if the player has no profiles linked, that means he doesn't
                # have a main_profile as well. Then we can just set the first
                # profile linked as the main one. We also don't need to do an
                # inner join, because once the player add his first profile,
                # it means he/she only has 1 profile linked.
                query = "SELECT id FROM profile WHERE member_id = $1"
                profile_id = await self.bot.pool.fetchval(query, ctx.author.id)
                await self.set_main_profile(ctx.author.id, profile_id)
        except Exception as exc:
            await ctx.send(embed=self.bot.embed_exception(exc))
        else:
            message = f'Profile successfully linked. Use "{ctx.prefix}profile list" to see your profile(s).'
            await ctx.send(message)

    @has_profile()
    @profile.command(aliases=["remove", "unbind"])
    @commands.cooldown(1, 3.0, commands.BucketType.member)
    async def unlink(self, ctx, index: Index):
        """Unlink your Overwatch profile from your Discord account.

        `[index]` - The profile's index you want to unlink.

        You can't unlink your main profile if you have more than 1 profile linked.
        """
        try:
            id, platform, username = await self.get_profile(ctx.author, index=index)
        except IndexError:
            await ctx.send(
                f'Invalid index. Use "{ctx.prefix}help unlink" for more info.'
            )
        except Exception as exc:
            await ctx.send(embed=self.bot.embed_exception(exc))

        profiles = await self.get_profiles(ctx.author)
        if await self.is_main_profile(ctx.author.id, id) and len(profiles) > 1:
            message = (
                "You can't unlink your main profile if you have multiple profiles set. "
                f'Use "{ctx.prefix}help profile main" for more info.'
            )
            return await ctx.send(message)

        if not await ctx.prompt(
            "Are you sure you want to unlink the following profile?\n"
            f"Platform: `{platform}`\n"
            f"Username: `{username}`"
        ):
            return
        try:
            await self.bot.pool.execute("DELETE FROM profile WHERE id = $1;", id)
        except Exception as exc:
            await ctx.send(embed=self.bot.embed_exception(exc))
        else:
            await ctx.send("Profile successfully unlinked.")

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 3.0, commands.BucketType.member)
    async def update(self, ctx, index: Index):
        """Update your Overwatch profile linked to your Discord account.

        `[index]` - The profile's index you want to update.
        """
        try:
            id, platform, username = await self.get_profile(ctx.author, index=index)
        except IndexError:
            await ctx.send(
                f'Invalid index. Use "{ctx.prefix}help update" for more info.'
            )
        except Exception as exc:
            await ctx.send(embed=self.bot.embed_exception(exc))

        title = "Update your Overwatch profile"
        platform = await Update(platform, username, title=title).start(ctx)
        username = await self.get_player_username(ctx, platform)
        if not username:
            return
        try:
            await self.update_profile(platform, username, profile_id=id)
        except Exception as exc:
            await ctx.send(embed=self.bot.embed_exception(exc))
        else:
            message = f'Profile successfully updated. Use "{ctx.prefix}profile list" to see the changes.'
            await ctx.send(message)

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 3.0, commands.BucketType.member)
    async def main(self, ctx, index: Index):
        """Updates your main profile.

        `[index]` - The profile's index you want to set as main.

        Defaults to the first profile you have linked.
        """
        try:
            id, platform, username = await self.get_profile(ctx.author, index=index)
            await self.set_main_profile(ctx.author.id, id)
        except IndexError:
            await ctx.send(f'Invalid index. Use "{ctx.prefix}help main" for more info.')
        except Exception as exc:
            await ctx.send(embed=self.bot.embed_exception(exc))
        else:
            embed = discord.Embed(color=ctx.author.color)
            embed.description = "Main profile successfully set to:"
            embed.add_field(name="Platform", value=platform)
            embed.add_field(name="Username", value=username)
            await ctx.send(embed=embed)

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 3.0, commands.BucketType.member)
    async def list(self, ctx, member: discord.Member = None):
        """Displays all member's profiles.

        `[member]` - The mention or the ID of a Discord member of the current server.

        If no member is given then the information returned will be yours.
        """
        try:
            member = member or ctx.author
            try:
                profiles = await self.get_profiles(member)
            except MemberHasNoProfile as exc:
                await ctx.send(exc)
            else:
                embed = await self.list_profiles(profiles, member)
        except Exception as exc:
            await ctx.send(embed=self.bot.embed_exception(exc))
        else:
            await ctx.send(embed=embed)

    @has_profile()
    @profile.command(aliases=["rank", "sr"])
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    async def rating(self, ctx, index: Index = None, member: discord.Member = None):
        """Shows a member's Overwatch ranks.

        `[index]` - The profile's index you want to see the ranks for.
        `[member]` - The mention or the ID of a Discord member of the current server.

        If no index is given then the profile used will be the main one.
        If no member is given then the ranks returned will be yours.

        If you want to see a Discord member's stats, you must give both the index of its
        profile and its mention.
        """
        async with ctx.typing():
            member = member or ctx.author
            try:
                id, platform, username = await self.get_profile(member, index=index)
            except MemberHasNoProfile as exc:
                await ctx.send(exc)
            except IndexError:
                await ctx.send(
                    f'Invalid index. Use "{ctx.prefix}help rating" for more info.'
                )
            except Exception as exc:
                await ctx.send(embed=self.bot.embed_exception(exc))
            else:
                try:
                    data = await Request(platform=platform, username=username).get()
                except RequestError as exc:
                    await ctx.send(exc)
                except Exception as exc:
                    await ctx.send(embed=self.bot.embed_exception(exc))
                else:
                    try:
                        profile = Player(
                            data=data, platform=platform, username=username
                        )
                        if profile.is_private:
                            embed = profile.private()
                        else:
                            embed = await profile.get_ratings(
                                ctx, save=True, profile_id=id
                            )
                    except Exception as exc:
                        await ctx.send(exc)
                    else:
                        await self.bot.paginator.Paginator(pages=embed).start(ctx)

    @has_profile()
    @profile.command(aliases=["stats"])
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    async def statistics(self, ctx, index: Index = None, member: discord.Member = None):
        """Shows a member's Overwatch both quick play and competitive statistics.

        `[index]` - The profile's index you want to see the statistics for.
        `[member]` - The mention or the ID of a Discord member of the current server.

        If no index is given then the profile used will be the main one.
        If no member is given then the statistics returned will be yours.

        If you want to see a Discord member's stats, you must give both the index of its
        profile and its mention.
        """
        async with ctx.typing():
            member = member or ctx.author
            try:
                _, platform, username = await self.get_profile(member, index=index)
            except MemberHasNoProfile as exc:
                await ctx.send(exc)
            except IndexError:
                await ctx.send(
                    f'Invalid index. Use "{ctx.prefix}help statistics" for more info.'
                )
            except Exception as exc:
                await ctx.send(embed=self.bot.embed_exception(exc))
            else:
                try:
                    data = await Request(platform=platform, username=username).get()
                except RequestError as exc:
                    await ctx.send(exc)
                except Exception as exc:
                    await ctx.send(embed=self.bot.embed_exception(exc))
                else:
                    try:
                        profile = Player(
                            data=data, platform=platform, username=username
                        )
                        if profile.is_private:
                            embed = profile.private()
                        else:
                            embed = profile.get_statistics(ctx)
                    except NoStatistics as exc:
                        await ctx.send(exc)
                    except Exception as exc:
                        await ctx.send(embed=self.bot.embed_exception(exc))
                    else:
                        await self.bot.paginator.Paginator(pages=embed).start(ctx)

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    async def hero(
        self, ctx, hero: Hero, index: Index = None, member: discord.Member = None
    ):
        """Shows a member's Overwatch both quick play and competitive statistics for a given hero.

        `<hero>` - The name of the hero you want to see stats for.
        `[index]` - The profile's index you want to see the ranks for.
        `[member]` - The mention or the ID of a Discord member of the current server.

        If no index is given then the profile used will be the main one.
        If no member is given then the statistics returned will be yours.

        If you want to see a Discord member's stats, you must give both the index of its
        profile and its mention.
        """
        async with ctx.typing():
            member = member or ctx.author
            try:
                _, platform, username = await self.get_profile(member, index=index)
            except MemberHasNoProfile as exc:
                await ctx.send(exc)
            except IndexError:
                await ctx.send(
                    f'Invalid index. Use "{ctx.prefix}help hero" for more info.'
                )
            except Exception as exc:
                await ctx.send(embed=self.bot.embed_exception(exc))
            else:
                try:
                    data = await Request(platform=platform, username=username).get()
                except RequestError as exc:
                    await ctx.send(exc)
                except Exception as exc:
                    await ctx.send(embed=self.bot.embed_exception(exc))
                else:
                    try:
                        profile = Player(
                            data=data, platform=platform, username=username
                        )
                        if profile.is_private:
                            embed = profile.private()
                        else:
                            embed = profile.get_hero(ctx, hero)
                    except NoHeroStatistics as exc:
                        await ctx.send(exc)
                    except Exception as exc:
                        await ctx.send(embed=self.bot.embed_exception(exc))
                    else:
                        await self.bot.paginator.Paginator(pages=embed).start(ctx)


def setup(bot):
    bot.add_cog(Profile(bot))
