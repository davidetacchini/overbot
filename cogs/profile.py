import asyncio
from io import BytesIO
from contextlib import suppress

import pandas as pd
import discord
import seaborn as sns
import matplotlib
from matplotlib import pyplot
from discord.ext import commands

from utils.i18n import _, locale
from utils.checks import is_premium, has_profile, can_add_profile
from utils.player import Player, NoStats, NoHeroStats
from utils.request import Request, RequestError
from utils.paginator import Link, Update
from classes.converters import Hero, Index

MAX_NICKNAME_LENGTH = 32

ROLES = {
    "tank": "\N{SHIELD}",
    "damage": "\N{CROSSED SWORDS}",
    "support": "\N{HEAVY GREEK CROSS}",
}


async def chunker(entries, chunk):
    for x in range(0, len(entries), chunk):
        yield entries[x : x + chunk]


class MemberHasNoProfile(Exception):
    """Exception raised when mentioned member has no profile connected."""

    def __init__(self, member):
        super().__init__(
            _("{member} hasn't linked a profile yet.").format(member=member)
        )


class MemberHasNoRatings(Exception):
    """Exception raised when mentioned member has not ratings saved."""

    def __init__(self):
        super().__init__(_("More data are needed in order for me to create a graph."))


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
        limit = self.bot.get_max_profiles_limit(member.id, member.guild.id)
        query = """SELECT profile.id, platform, username
                   FROM profile
                   INNER JOIN member
                           ON member.id = profile.member_id
                   WHERE member.id = $1
                   LIMIT $2;
                """
        profiles = await self.bot.pool.fetch(query, member.id, limit)
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

    async def list_profiles(self, ctx, profiles):
        pages = []
        chunks = [c async for c in chunker(profiles, 10)]
        index = 1  # avoid resetting index to 1 every page
        limit = self.bot.get_max_profiles_limit(ctx.author.id, ctx.guild.id)

        for chunk in chunks:
            embed = discord.Embed(color=self.bot.color(ctx.author.id))
            embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
            embed.set_footer(
                text=_("{profiles}/{limit} profiles").format(
                    profiles=len(profiles), limit=limit
                )
            )

            description = []
            for (id, platform, username) in chunk:
                if platform == "pc":
                    username = username.replace("-", "#")
                if not await self.is_main_profile(ctx.author.id, profile_id=id):
                    fmt = f"{index}. {self.platforms.get(platform)} - {username}"
                else:
                    fmt = f"{index}. {self.platforms.get(platform)} - {username} :star:"
                description.append(fmt)
                index += 1
            embed.description = "\n".join(description)
            pages.append(embed)
        return pages

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
    @locale
    async def profile(self, ctx, command: str = None):
        _("""Displays a list with all profile's subcommands.""")
        embed = self.bot.get_subcommands(ctx, ctx.command)
        await ctx.send(embed=embed)

    @can_add_profile()
    @profile.command(aliases=["add", "bind"])
    @locale
    async def link(self, ctx):
        _("""Link your Overwatch profile(s) to your Discord account.""")
        platform = await Link().start(ctx)
        username = await self.get_player_username(ctx, platform)

        if not username:
            return

        try:
            await self.insert_profile(platform, username, member_id=ctx.author.id)
            if not await self.has_main_profile(ctx.author.id):
                # if the player has no profiles linked, that means he doesn't
                # have a main_profile as well. Then we can just set the first
                # profile linked as the main one
                query = "SELECT id FROM profile WHERE member_id = $1;"
                profile_id = await self.bot.pool.fetchval(query, ctx.author.id)
                await self.set_main_profile(ctx.author.id, profile_id=profile_id)
        except Exception as e:
            await ctx.send(embed=self.bot.embed_exception(e))
        else:
            await ctx.send(_("Profile successfully linked."))

    @has_profile()
    @profile.command(aliases=["remove", "unbind"])
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
            return await ctx.send(_("Invalid index."))

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
                "Platform: `{platform}`\n"
                "Username: `{username}`"
            ).format(platform=platform, username=username)
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
            return await ctx.send(_("Invalid index."))

        try:
            platform = await Update(platform, username).start(ctx)
            username = await self.get_player_username(ctx, platform)
        except Exception as e:
            return await ctx.send(embed=self.bot.embed_exception(e))

        if not username:
            return

        if platform == "pc":
            username = username.replace("-", "#")

        try:
            await self.update_profile(platform, username, profile_id=id)
        except Exception as e:
            await ctx.send(embed=self.bot.embed_exception(e))
        else:
            await ctx.send("Profile successfully updated.")

    @has_profile()
    @profile.command()
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
            return await ctx.send(_("Invalid index."))

        await self.set_main_profile(ctx.author.id, profile_id=id)
        embed = discord.Embed(color=self.bot.color(ctx.author.id))
        embed.description = _("Main profile successfully set to:")
        embed.add_field(name=_("Platform"), value=platform)
        embed.add_field(name=_("Username"), value=username)
        await ctx.send(embed=embed)

    @has_profile()
    @profile.command()
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

        embed = await self.list_profiles(ctx, profiles)
        await self.bot.paginator.Paginator(pages=embed).start(ctx)

    @has_profile()
    @profile.command(aliases=["rank", "sr"])
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
                return await ctx.send(_("Invalid index."))

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
    @profile.command(aliases=["statistics"])
    @locale
    async def stats(self, ctx, index: Index = None, member: discord.Member = None):
        _(
            """Shows a member's Overwatch both quick play and competitive stats.

        `[index]` - The profile's index you want to see the stats for.
        `[member]` - The mention or the ID of a Discord member of the current server.

        If no index is given then the profile used will be the main one.
        If no member is given then the stats returned will be yours.

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
                return await ctx.send(_("Invalid index."))

            try:
                data = await Request(platform=platform, username=username).get()
            except RequestError as e:
                return await ctx.send(e)

            profile = Player(data, platform=platform, username=username)
            if profile.is_private:
                embed = profile.private()
            else:
                try:
                    embed = profile.get_stats(ctx)
                except NoStats as e:
                    return await ctx.send(e)
                await self.bot.paginator.Paginator(pages=embed).start(ctx)

    @has_profile()
    @profile.command()
    @locale
    async def hero(
        self, ctx, hero: Hero, index: Index = None, member: discord.Member = None
    ):
        _(
            """Shows a member's Overwatch both quick play and competitive stats for a given hero.

        `<hero>` - The name of the hero you want to see stats for.
        `[index]` - The profile's index you want to see the ranks for.
        `[member]` - The mention or the ID of a Discord member of the current server.

        If no index is given then the profile used will be the main one.
        If no member is given then the stats returned will be yours.

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
                return await ctx.send(_("Invalid index."))

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
                except NoHeroStats as e:
                    return await ctx.send(e)
            await self.bot.paginator.Paginator(pages=embed).start(ctx)

    @has_profile()
    @profile.command(aliases=["nick"])
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

    async def sr_graph(self, ctx, *, profile):
        profile_id, platform, username = profile

        query = """SELECT tank, damage, support, date
                   FROM rating
                   INNER JOIN profile
                           ON profile.id = rating.profile_id
                   WHERE profile.id = $1
                """

        ratings = await self.bot.pool.fetch(query, profile_id)

        sns.set()
        sns.set_style("darkgrid")

        data = pd.DataFrame.from_records(
            ratings,
            columns=["tank", "damage", "support", "date"],
            index="date",
        )

        for row in ["support", "damage", "tank"]:
            if data[row].isnull().all():
                data.drop(row, axis=1, inplace=True)

        if len(data.columns) == 0:
            raise MemberHasNoRatings()

        fig, ax = pyplot.subplots()
        ax.xaxis_date()

        sns.lineplot(data=data, ax=ax, linewidth=2.5)
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y-%m-%d"))
        fig.autofmt_xdate()

        username = username.replace("-", "#")
        fig.suptitle(f"{username} - {platform}", fontsize="20")
        pyplot.legend(title="Roles", loc="upper right")
        pyplot.xlabel("Date")
        pyplot.ylabel("SR")

        image = BytesIO()
        pyplot.savefig(format="png", fname=image, transparent=False)
        image.seek(0)

        file = discord.File(image, filename="graph.png")

        embed = discord.Embed(color=self.bot.color(ctx.author.id))
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        embed.set_image(url="attachment://graph.png")
        return file, embed

    @is_premium()
    @has_profile()
    @profile.command()
    @locale
    async def graph(self, ctx, index: Index = None):
        _(
            """`[Premium]` Displays a profile's SR graph performance.

        `[index]` - The profile's index you want to see the SR graph for.

        If no index is given then the profile used will be the main one.
        """
        )
        try:
            profile = await self.get_profile(ctx.author, index=index)
        except MemberHasNoProfile as e:
            return await ctx.send(e)
        except IndexError:
            return await ctx.send(_("Invalid index."))

        try:
            file, embed = await self.sr_graph(ctx, profile=profile)
        except MemberHasNoRatings as e:
            await ctx.send(e)
        except Exception as e:
            await ctx.send(embed=self.bot.embed_exception(e))
        else:
            await ctx.send(file=file, embed=embed)


def setup(bot):
    bot.add_cog(Profile(bot))
