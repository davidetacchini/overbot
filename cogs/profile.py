import asyncio

from io import BytesIO

import pandas as pd
import discord
import seaborn as sns
import matplotlib

from asyncpg import Record
from matplotlib import pyplot
from discord.ext import commands

from utils.funcs import chunker, get_platform_emoji
from utils.checks import is_premium, has_profile
from classes.player import Player
from classes.context import Context
from classes.request import Request
from classes.nickname import Nickname
from classes.paginator import ProfileManagerView, choose_profile, choose_platform
from classes.converters import Hero
from classes.exceptions import NoChoice


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_profiles(self, ctx: "Context", member: discord.Member):
        limit = self.bot.get_profiles_limit(ctx, member.id)
        query = """SELECT profile.id, platform, username
                   FROM profile
                   INNER JOIN member
                           ON member.id = profile.member_id
                   WHERE member.id = $1
                   LIMIT $2;
                """
        return await self.bot.pool.fetch(query, member.id, limit)

    async def get_profile(self, profile_id: str) -> Record:
        query = """SELECT id, platform, username
                   FROM profile
                   WHERE id = $1;
                """
        return await self.bot.pool.fetchrow(query, int(profile_id))

    async def list_profiles(
        self, ctx: "Context", member_id: int, profiles: list[Record]
    ) -> list[discord.Embed]:
        embed = discord.Embed(color=self.bot.color(ctx.author.id))
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar)

        if not profiles:
            embed.description = "No profiles..."
            return embed

        chunks = [c async for c in chunker(profiles, per_page=10)]
        index = 1  # avoid resetting index to 1 every page
        limit = self.bot.get_profiles_limit(ctx, member_id)

        pages = []
        for chunk in chunks:
            embed = embed.copy()
            embed.set_footer(text=f"{len(profiles)}/{limit} profiles")
            description = []
            for (id_, platform, username) in chunk:
                if platform == "pc":
                    username = username.replace("-", "#")
                description.append(f"{index}. {get_platform_emoji(platform)} - {username}")
                index += 1
            embed.description = "\n".join(description)
            pages.append(embed)
        return pages

    async def get_player_username(self, ctx, platform):
        mention = ctx.author.mention

        match platform:
            case "pc":
                await ctx.send(f"{mention}, enter your BattleTag (format: name#0000):")
            case "psn":
                await ctx.send(f"{mention}, enter your Online ID:")
            case "xbl":
                await ctx.send(f"{mention}, enter your Gamertag:")
            case "nintendo-switch":
                await ctx.send(f"{mention}, enter your Nintendo Network ID:")

        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

        try:
            message = await self.bot.wait_for("message", check=check, timeout=60.0)
        except asyncio.TimeoutError:
            raise NoChoice() from None
        else:
            return message.content.replace("#", "-")

    @commands.group(invoke_without_command=True)
    async def profile(self, ctx: "Context", member: discord.Member = None) -> None:
        """Manages your profiles.

        `[member]` - The mention or the ID of a Discord member.

        If no member is given, the profiles returned will be yours.
        """
        member = member or ctx.author
        profiles = await self.get_profiles(ctx, member)
        entries = await self.list_profiles(ctx, member.id, profiles)

        if member != ctx.author:
            return await self.bot.paginate(entries, ctx=ctx)

        view = ProfileManagerView(entries, ctx=ctx)

        if not profiles:
            view.unlink.disabled = True
            view.update.disabled = True

        await view.start()
        await view.wait()

        match view.action:
            case "link":
                await self.link_profile(ctx)
            case "unlink":
                await self.unlink_profile(ctx)
            case "update":
                await self.update_profile(ctx)

    async def link_profile(self, ctx: "Context") -> None:
        platform = await choose_platform(ctx)
        username = await self.get_player_username(ctx, platform)

        if not username:
            return

        query = "INSERT INTO profile(platform, username, member_id) VALUES($1, $2, $3);"
        await self.bot.pool.execute(query, platform, username, ctx.author.id)
        await ctx.send("Profile successfully linked.")

    async def unlink_profile(self, ctx: "Context") -> None:
        message = "Select a profile to unlink."
        profile_id = await choose_profile(ctx, message, ctx.author)
        id_, platform, username = await self.get_profile(profile_id)

        if platform == "pc":
            username = username.replace("-", "#")

        embed = discord.Embed(color=self.bot.color(ctx.author.id))
        embed.title = "Are you sure you want to unlink the following profile?"
        embed.add_field(name="Platform", value=platform)
        embed.add_field(name="Username", value=username)

        if await ctx.prompt(embed):
            await self.bot.pool.execute("DELETE FROM profile WHERE id = $1;", id_)
            await ctx.send("Profile successfully deleted.")

    async def update_profile(self, ctx: "Context") -> None:
        message = "Select a profile to update."
        profile_id = await choose_profile(ctx, message, ctx.author)
        id_, platform, username = await self.get_profile(profile_id)
        platform = await choose_platform(ctx)
        username = await self.get_player_username(ctx, platform)

        if not username:
            return

        if platform == "pc":
            username = username.replace("-", "#")

        query = "UPDATE profile SET platform = $1, username = $2 WHERE id = $3;"
        await self.bot.pool.execute(query, platform, username, int(profile_id))
        await ctx.send("Profile successfully updated.")

    @has_profile()
    @profile.command(aliases=["rank", "sr"])
    async def rating(self, ctx: "Context", member: discord.Member = None) -> None:
        """Provides SRs information for a profile.

        `[member]` - The mention or the ID of a Discord member.

        If no member is given, the ratings returned will be yours.
        """
        member = member or ctx.author
        message = "Select a profile to view the skill ratings for."
        profile_id = await choose_profile(ctx, message, member)
        id_, platform, username = await self.get_profile(profile_id)

        data = await Request(platform, username).get()
        profile = Player(data, platform=platform, username=username)
        if profile.is_private():
            embed = profile.embed_private()
        else:
            embed = await profile.embed_ratings(ctx, save=True, profile_id=id_)
            # only updates nickname with the profile set for that purspose
            query = "SELECT * FROM nickname WHERE profile_id = $1"
            flag = await self.bot.pool.fetchrow(query, id_)
            if flag and member.id == ctx.author.id:
                nick = Nickname(ctx, profile=profile)
                await nick.update()
        await ctx.send(embed=embed)

    @has_profile()
    @profile.command()
    async def stats(self, ctx: "Context", member: discord.Member = None) -> None:
        """Provides general stats for a profile.

        `[member]` - The mention or the ID of a Discord member.

        If no member is given, the stats returned will be yours.
        """
        member = member or ctx.author
        message = "Select a profile to view the stats for."
        profile_id = await choose_profile(ctx, message, member)
        _, platform, username = await self.get_profile(profile_id)

        await self.bot.get_cog("Stats").show_stats_for(ctx, "allHeroes", platform, username)

    @has_profile()
    @profile.command()
    async def hero(self, ctx: "Context", hero: Hero, member: discord.Member = None) -> None:
        """Provides general hero stats for a profile.

        `<hero>` - The name of the hero to see stats for.
        `[member]` - The mention or the ID of a Discord member.

        If no member is given, the stats returned will be yours.
        """
        member = member or ctx.author
        message = f"Select a profile to view **{hero}** stats for."
        profile_id = await choose_profile(ctx, message, member)
        _, platform, username = await self.get_profile(profile_id)

        await self.bot.get_cog("Stats").show_stats_for(ctx, hero, platform, username)

    @has_profile()
    @profile.command()
    async def summary(self, ctx: "Context", member: discord.Member = None) -> None:
        """Provides summarized stats for a profile.

        `[member]` - The mention or the ID of a Discord member.

        If no member is given, the stats returned will be yours.
        """
        member = member or ctx.author
        message = "Select a profile to view the summary for."
        profile_id = await choose_profile(ctx, message, member)
        _, platform, username = await self.get_profile(profile_id)
        data = await Request(platform, username).get()
        profile = Player(data, platform=platform, username=username)
        if profile.is_private():
            embed = profile.embed_private()
        else:
            embed = profile.embed_summary(ctx)
        await ctx.send(embed=embed)

    @has_profile()
    @profile.command(aliases=["nick"])
    @commands.guild_only()
    async def nickname(self, ctx: "Context") -> None:
        """Shows or remove your SRs in your nickname.

        The nickname can only be set in one server. It updates
        automatically whenever `profile rating` is used and the
        profile matches the one set for the nickname.
        """
        nick = Nickname(ctx)
        if not await nick.exists():
            if not await ctx.prompt("This will display your SRs in your nickname."):
                return

            if ctx.guild.me.top_role < ctx.author.top_role:
                return await ctx.send(
                    "This server's owner needs to move the `OverBot` role higher, so I will "
                    "be able to update your nickname. If you are this server's owner, there's "
                    "not way for me to change your nickname, sorry!"
                )

            message = "Select a profile to use for the nickname SRs."
            profile_id = await choose_profile(ctx, message, ctx.author)
            id_, platform, username = await self.get_profile(profile_id)
            data = await Request(platform, username).get()
            profile = Player(data, platform=platform, username=username)
            nick.profile = profile

            if profile.is_private():
                return await ctx.send(embed=profile.embed_private())

            try:
                await nick.set_or_remove(profile_id=id_)
            except Exception as e:
                await ctx.send(e)
        else:
            if await ctx.prompt("This will remove your SR in your nickname."):
                try:
                    await nick.set_or_remove(remove=True)
                except Exception as e:
                    await ctx.send(e)

    async def sr_graph(self, ctx: "Context", profile: Record):
        id_, platform, username = profile

        query = """SELECT tank, damage, support, date
                   FROM rating
                   INNER JOIN profile
                           ON profile.id = rating.profile_id
                   WHERE profile.id = $1
                """

        ratings = await self.bot.pool.fetch(query, id_)

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
            raise commands.BadArgument("I don't have enough data to create the graph.")

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
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar)
        embed.set_image(url="attachment://graph.png")
        return file, embed

    @is_premium()
    @has_profile()
    @profile.command()
    async def graph(self, ctx: "Context") -> None:
        """`[Premium]` Shows SRs performance graph."""
        message = "Select a profile to view the SRs graph for."
        profile_id = await choose_profile(ctx, message, ctx.author)
        profile = await self.get_profile(profile_id)
        file, embed = await self.sr_graph(ctx, profile)
        await ctx.send(file=file, embed=embed)


def setup(bot):
    bot.add_cog(Profile(bot))
