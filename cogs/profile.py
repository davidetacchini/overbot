import asyncio
from contextlib import suppress

import discord
from discord.ext import commands

from utils.i18n import _, locale
from utils.checks import has_profile, can_add_profile
from utils.player import Player, NoStatistics, NoHeroStatistics
from utils.request import Request, RequestError
from utils.paginator import Link, Update
from classes.converters import Hero, Index

MAX_NICKNAME_LENGTH = 32

ROLES = {
    "tank": "\N{SHIELD}",
    "damage": "\N{CROSSED SWORDS}",
    "support": "\N{HEAVY GREEK CROSS}",
}


class MemberHasNoProfile(Exception):
    """Exception raised when mentioned member has no profile connected."""

    def __init__(self, member):
        super().__init__(_(f"{member} hasn't linked a profile yet."))


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

    async def set_main_profile(self, member_id, *, profile_id):
        query = "UPDATE member SET main_profile = $1 WHERE id = $2;"
        await self.bot.pool.execute(query, profile_id, member_id)

    async def is_main_profile(self, member_id, *, profile_id):
        query = "SELECT main_profile FROM member WHERE id = $1;"
        return await self.bot.pool.fetchval(query, member_id) == profile_id

    async def has_main_profile(self, member_id):
        query = "SELECT main_profile FROM member WHERE id = $1;"
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
            text=_(f"The star indicates the main profile - {profiles}/5").format(
                profiles=len(profiles)
            )
        )
        description = []
        for index, (id, platform, username) in enumerate(profiles, start=1):
            if platform == "pc":
                username = username.replace("-", "#")
            if not await self.is_main_profile(member.id, profile_id=id):
                fmt = f"{index}. {platform} - {username}"
            else:
                fmt = f"{index}. {platform} - {username} :star:"
            description.append(fmt)
        embed.description = "\n".join(description)
        return embed

    async def get_player_username(self, ctx, platform):
        if platform == "pc":
            await ctx.send(_("Enter your BattleTag (format: name#0000):"))
        elif platform == "psn":
            await ctx.send(_("Enter your Online ID:"))
        elif platform == "xbl":
            await ctx.send(_("Enter your Gamertag:"))
        elif platform == "nintendo-switch":
            await ctx.send(_("Enter your Nintendo Switch ID:"))
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
            await ctx.send(_("You took too long to reply."))
        else:
            return message.content.replace("#", "-")

    async def has_nickname(self, member_id):
        query = "SELECT id FROM nickname WHERE id = $1;"
        return await self.bot.pool.fetchval(query, member_id)

    async def make_nickname(self, member, *, profile):
        ratings = profile.resolve_ratings()
        if not ratings:
            return f"{member.name[:21]} [Unranked]"

        tmp = ""
        for key, value in ratings.items():
            tmp += f"{ROLES.get(key)}{value}/"

        # tmp[:-1] removes the last slash
        tmp = "[" + tmp[:-1] + "]"

        # dinamically assign the nickname's length based on
        # player's SR. -1 indicates the space between
        # the member's name and the SR
        x = MAX_NICKNAME_LENGTH - len(tmp) - 1
        name = member.name[:x]
        return name + " " + tmp

    async def set_or_remove_nickname(
        self, ctx, *, profile=None, profile_id=None, remove=False
    ):
        member = ctx.author

        if not remove:
            nick = await self.make_nickname(member, profile=profile)
        else:
            nick = None

        try:
            await member.edit(nick=nick)
        except discord.Forbidden:
            await ctx.send(
                _(
                    "I can't change nicknames in this server. Grant me `Manage Nicknames` permission."
                )
            )
        except discord.HTTPException:
            await ctx.send(
                _(
                    "Something bad happened while updating your nickname. Please try again."
                )
            )

        if not remove:
            query = (
                "INSERT INTO nickname(id, server_id, profile_id) VALUES($1, $2, $3);"
            )
            await self.bot.pool.execute(query, member.id, ctx.guild.id, profile_id)
            await ctx.send(
                _(
                    "Nickname successfully set. Your SR will now be visible in your nickname within this server."
                )
            )
        else:
            query = "DELETE FROM nickname WHERE id = $1;"
            await self.bot.pool.execute(query, member.id)
            await ctx.send(_("Nickname successfully removed."))

    async def update_nickname_sr(self, member, *, profile):
        if not await self.has_nickname(member.id):
            return

        nick = await self.make_nickname(member, profile=profile)
        with suppress(Exception):
            await member.edit(nick=nick)

    @commands.group(invoke_without_command=True)
    @commands.cooldown(1, 1.0, commands.BucketType.member)
    @locale
    async def profile(self, ctx, command: str = None):
        _("""Displays a list with all profile's subcommands.""")
        embed = self.bot.get_subcommands(ctx, ctx.command)
        await ctx.send(embed=embed)

    @can_add_profile()
    @profile.command(aliases=["add", "bind"])
    @commands.cooldown(1, 3.0, commands.BucketType.member)
    @locale
    async def link(self, ctx):
        _("""Link your Overwatch profile(s) to your Discord account.""")
        title = _("Link your Overwatch profile to your Discord ID")
        platform = await Link(title=title).start(ctx)
        username = await self.get_player_username(ctx, platform)

        if not username:
            return

        try:
            await self.insert_profile(platform, username, member_id=ctx.author.id)
            if not await self.has_main_profile(ctx.author.id):
                # if the player has no profiles linked, that means he doesn't
                # have a main_profile as well. Then we can just set the first
                # profile linked as the main one.
                query = "SELECT id FROM profile WHERE member_id = $1;"
                profile_id = await self.bot.pool.fetchval(query, ctx.author.id)
                await self.set_main_profile(ctx.author.id, profile_id=profile_id)
        except Exception as e:
            await ctx.send(embed=self.bot.embed_exception(e))
        else:
            message = _(
                'Profile successfully linked. Use "{prefix}profile list" to see your profile(s).'
            ).format(prefix=ctx.prefix)
            await ctx.send(message)

    @has_profile()
    @profile.command(aliases=["remove", "unbind"])
    @commands.cooldown(1, 3.0, commands.BucketType.member)
    @locale
    async def unlink(self, ctx, index: Index):
        _(
            """Unlink your Overwatch profile from your Discord account.

        `<index>` - The profile's index you want to unlink.

        You can't unlink your main profile if you have more than 1 profile linked.
        """
        )
        try:
            id, platform, username = await self.get_profile(ctx.author, index=index)
        except IndexError:
            return await ctx.send(
                _(
                    'Invalid index. Use "{prefix}help profile unlink" for more info.'
                ).format(prefix=ctx.prefix)
            )

        profiles = await self.get_profiles(ctx.author)
        if (
            await self.is_main_profile(ctx.author.id, profile_id=id)
            and len(profiles) > 1
        ):
            message = _(
                "You can't unlink your main profile if you have multiple profiles set. "
                'Use "{prefix}help profile main" for more info.'
            ).format(prefix=ctx.prefix)
            return await ctx.send(message)

        if platform == "pc":
            username = username.replace("-", "#")

        if not await ctx.prompt(
            _(
                "Are you sure you want to unlink the following profile?\n"
                f"Platform: `{platform}`\n"
                f"Username: `{username}`"
            )
        ):
            return

        try:
            await self.bot.pool.execute("DELETE FROM profile WHERE id = $1;", id)
        except Exception as e:
            await ctx.send(embed=self.bot.embed_exception(e))
        else:
            await ctx.send(_("Profile successfully unlinked."))

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 3.0, commands.BucketType.member)
    @locale
    async def update(self, ctx, index: Index):
        _(
            """Update your Overwatch profile linked to your Discord account.

        `<index>` - The profile's index you want to update.
        """
        )
        try:
            id, platform, username = await self.get_profile(ctx.author, index=index)
        except IndexError:
            return await ctx.send(
                _(
                    'Invalid index. Use "{prefix}help profile update" for more info.'
                ).format(prefix=ctx.prefix)
            )

        title = _("Update your Overwatch profile")
        platform = await Update(platform, username, title=title).start(ctx)
        username = await self.get_player_username(ctx, platform)

        if not username:
            return

        if platform == "pc":
            username = username.replace("-", "#")

        try:
            await self.update_profile(platform, username, profile_id=id)
        except Exception as e:
            await ctx.send(embed=self.bot.embed_exception(e))
        else:
            message = _(
                'Profile successfully updated. Use "{prefix}profile list" to see the changes.'
            ).format(prefix=ctx.prefix)
            await ctx.send(message)

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 3.0, commands.BucketType.member)
    @locale
    async def main(self, ctx, index: Index):
        _(
            """Updates your main profile.

        `<index>` - The profile's index you want to set as main.

        Defaults to the first profile you have linked.
        """
        )
        try:
            id, platform, username = await self.get_profile(ctx.author, index=index)
        except IndexError:
            return await ctx.send(
                _(
                    'Invalid index. Use "{prefix}help profile main" for more info.'
                ).format(prefix=ctx.prefix)
            )

        await self.set_main_profile(ctx.author.id, profile_id=id)
        embed = discord.Embed(color=ctx.author.color)
        embed.description = _("Main profile successfully set to:")
        embed.add_field(name=_("Platform"), value=platform)
        embed.add_field(name=_("Username"), value=username)
        await ctx.send(embed=embed)

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 3.0, commands.BucketType.member)
    @locale
    async def list(self, ctx, member: discord.Member = None):
        _(
            """Displays all member's profiles.

        `[member]` - The mention or the ID of a Discord member of the current server.

        If no member is given then the information returned will be yours.
        """
        )
        member = member or ctx.author

        try:
            profiles = await self.get_profiles(member)
        except MemberHasNoProfile as e:
            return await ctx.send(e)

        embed = await self.list_profiles(profiles, member)
        await ctx.send(embed=embed)

    @has_profile()
    @profile.command(aliases=["rank", "sr"])
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    @locale
    async def rating(self, ctx, index: Index = None, member: discord.Member = None):
        _(
            """Shows a member's Overwatch ranks.

        `[index]` - The profile's index you want to see the ranks for.
        `[member]` - The mention or the ID of a Discord member of the current server.

        If no index is given then the profile used will be the main one.
        If no member is given then the ranks returned will be yours.

        If you want to see a member's stats, you must enter both the index and the member.
        """
        )
        async with ctx.typing():
            member = member or ctx.author

            try:
                id, platform, username = await self.get_profile(member, index=index)
            except MemberHasNoProfile as e:
                return await ctx.send(e)
            except IndexError:
                return await ctx.send(
                    _(
                        'Invalid index. Use "{prefix}help profile rating" for more info.'
                    ).format(prefix=ctx.prefix)
                )

            try:
                data = await Request(platform=platform, username=username).get()
            except RequestError as e:
                return await ctx.send(e)

            profile = Player(data, platform=platform, username=username)
            if profile.is_private:
                embed = profile.private()
            else:
                embed = await profile.get_ratings(ctx, save=True, profile_id=id)
                # if the index is None that means it's the main profile
                if not index and member.id == ctx.author.id:
                    await self.update_nickname_sr(ctx.author, profile=profile)
            await self.bot.paginator.Paginator(pages=embed).start(ctx)

    @has_profile()
    @profile.command(aliases=["stats"])
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    @locale
    async def statistics(self, ctx, index: Index = None, member: discord.Member = None):
        _(
            """Shows a member's Overwatch both quick play and competitive statistics.

        `[index]` - The profile's index you want to see the statistics for.
        `[member]` - The mention or the ID of a Discord member of the current server.

        If no index is given then the profile used will be the main one.
        If no member is given then the statistics returned will be yours.

        If you want to see a member's stats, you must enter both the index and the member.
        """
        )
        async with ctx.typing():
            member = member or ctx.author

            try:
                # using 'unused' instead of '_' since it conflicts with gettext _()
                unused, platform, username = await self.get_profile(member, index=index)
            except MemberHasNoProfile as e:
                return await ctx.send(e)
            except IndexError:
                return await ctx.send(
                    _(
                        'Invalid index. Use "{prefix}help profile statistics" for more info.'
                    ).format(prefix=ctx.prefix)
                )

            try:
                data = await Request(platform=platform, username=username).get()
            except RequestError as e:
                return await ctx.send(e)

            profile = Player(data, platform=platform, username=username)
            if profile.is_private:
                embed = profile.private()
            else:
                try:
                    embed = profile.get_statistics(ctx)
                except NoStatistics as e:
                    return await ctx.send(e)
                await self.bot.paginator.Paginator(pages=embed).start(ctx)

    @has_profile()
    @profile.command()
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    @locale
    async def hero(
        self, ctx, hero: Hero, index: Index = None, member: discord.Member = None
    ):
        _(
            """Shows a member's Overwatch both quick play and competitive statistics for a given hero.

        `<hero>` - The name of the hero you want to see stats for.
        `[index]` - The profile's index you want to see the ranks for.
        `[member]` - The mention or the ID of a Discord member of the current server.

        If no index is given then the profile used will be the main one.
        If no member is given then the statistics returned will be yours.

        If you want to see a member's stats, you must enter both the index and the member.
        """
        )
        async with ctx.typing():
            member = member or ctx.author

            try:
                unused, platform, username = await self.get_profile(member, index=index)
            except MemberHasNoProfile as e:
                return await ctx.send(e)
            except IndexError:
                return await ctx.send(
                    _(
                        'Invalid index. Use "{prefix}help profile hero" for more info.'
                    ).format(prefix=ctx.prefix)
                )

            try:
                data = await Request(platform=platform, username=username).get()
            except RequestError as e:
                return await ctx.send(e)

            profile = Player(data, platform=platform, username=username)
            if profile.is_private:
                embed = profile.private()
            else:
                try:
                    embed = profile.get_hero(ctx, hero)
                except NoHeroStatistics as e:
                    return await ctx.send(e)
            await self.bot.paginator.Paginator(pages=embed).start(ctx)

    @has_profile()
    @profile.command(aliases=["nick"])
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    @commands.guild_only()
    @locale
    async def nickname(self, ctx):
        _(
            """Update your server nickname and set it to your SR.

        The nickname can only be set in one server.

        The nickname will automatically be updated everytime `-profile rating` is used
        and the profile is the main one.
        """
        )
        if not await self.has_nickname(ctx.author.id):
            if not await ctx.prompt(
                _("Do you want to display your SR in your nickname?")
            ):
                return

            if ctx.guild.me.top_role < ctx.author.top_role:
                return await ctx.send(
                    _(
                        "This server's owner needs to move the `OverBot` role higher, so I will "
                        "be able to update your nickname. If you are this server's owner, there's "
                        "not way for me to change your nickname, sorry!"
                    )
                )

            id, platform, username = await self.get_profile(ctx.author, index=None)
            try:
                data = await Request(platform=platform, username=username).get()
            except RequestError as e:
                return await ctx.send(e)

            profile = Player(data, platform=platform, username=username)
            if profile.is_private:
                return await ctx.send(embed=profile.private())

            try:
                await self.set_or_remove_nickname(ctx, profile=profile, profile_id=id)
            except Exception as e:
                await ctx.send(e)
        else:
            if await ctx.prompt(
                _("Do you want to **remove** your SR in your nickname?")
            ):
                try:
                    await self.set_or_remove_nickname(ctx, remove=True)
                except Exception as e:
                    await ctx.send(e)


def setup(bot):
    bot.add_cog(Profile(bot))
