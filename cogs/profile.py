from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

import pandas as pd
import discord
import seaborn as sns
import matplotlib

from discord import app_commands
from matplotlib import pyplot
from discord.ext import commands

from classes.ui import ModalProfileLink, SelectProfileView, ModalProfileUpdate, SelectProfilesView
from utils.funcs import chunker, hero_autocomplete, get_platform_emoji
from utils.checks import is_premium, has_profile, can_add_profile
from classes.profile import Profile
from classes.nickname import Nickname
from classes.exceptions import NoChoice, CannotCreateGraph

if TYPE_CHECKING:
    from asyncpg import Record

    from bot import OverBot


class ProfileCog(commands.Cog, name="Profile"):
    def __init__(self, bot: OverBot):
        self.bot = bot

    profile = app_commands.Group(name="profile", description="Your Overwatch profiles.")

    async def get_profiles(self, interaction: discord.Interaction, member_id: int) -> list[Record]:
        limit = self.bot.get_profiles_limit(interaction, member_id)
        query = """SELECT profile.id, platform, username
                   FROM profile
                   INNER JOIN member
                           ON member.id = profile.member_id
                   WHERE member.id = $1
                   LIMIT $2;
                """
        return await self.bot.pool.fetch(query, member_id, limit)

    async def get_profile(self, profile_id: str) -> Record:
        query = """SELECT id, platform, username
                   FROM profile
                   WHERE id = $1;
                """
        return await self.bot.pool.fetchrow(query, int(profile_id))

    async def select_profile(
        interaction: discord.Interaction, message: str, member: None | discord.Member = None
    ) -> str:
        member = member or interaction.user
        profiles = await interaction.client.get_cog("Profile").get_profiles(interaction, member.id)

        # if there only is a profile then just return it
        if len(profiles) == 1:
            profile_id, _, _ = profiles[0]
            return await interaction.client.get_cog("Profile").get_profile(profile_id)

        view = SelectProfileView(profiles, author_id=interaction.user.id)

        if interaction.response.is_done():
            view.message = await interaction.followup.send(message, view=view)
        else:
            view.message = await interaction.response.send_message(message, view=view)
        await view.wait()

        choice = view.select.values[0] if len(view.select.values) else None

        if choice is not None:
            return await interaction.client.get_cog("Profile").get_profile(choice)
        raise NoChoice() from None

    async def list_profiles(
        self, interaction: discord.Interaction, member: discord.Member, profiles: list[Record]
    ) -> list[discord.Embed]:
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.set_author(name=member, icon_url=member.display_avatar)

        if not profiles:
            embed.description = "No profiles..."
            embed.set_footer(text=f"Requested by {interaction.user}")
            return embed

        chunks = [c async for c in chunker(profiles, per_page=10)]
        limit = self.bot.get_profiles_limit(interaction, member.id)

        pages = []
        for chunk in chunks:
            embed = embed.copy()
            embed.set_footer(
                text=f"{len(profiles)}/{limit} profiles • Requested by {interaction.user}"
            )
            description = []
            for (id_, platform, username) in chunk:
                description.append(f"{get_platform_emoji(platform)} {username}")
            embed.description = "\n".join(description)
            pages.append(embed)
        return pages

    @profile.command()
    @app_commands.describe(member="The mention or the ID of a Discord member")
    async def list(self, interaction: discord.Interaction, member: None | discord.Member = None):
        """List your own or a member's profiles"""
        member = member or interaction.user
        profiles = await self.get_profiles(interaction, member.id)
        entries = await self.list_profiles(interaction, member, profiles)
        return await self.bot.paginate(entries, interaction=interaction)

    @can_add_profile()
    @profile.command()
    async def link(self, interaction: discord.Interaction):
        """Link an Overwatch profile"""
        await interaction.response.send_modal(ModalProfileLink())

    @has_profile()
    @profile.command()
    async def update(self, interaction: discord.Interaction):
        """Update an Overwatch profile"""
        profiles = await self.get_profiles(interaction, interaction.user.id)
        await interaction.response.send_modal(ModalProfileUpdate(profiles))

    @has_profile()
    @profile.command()
    async def unlink(self, interaction: discord.Interaction):
        """Unlink an Overwatch profile"""
        profiles = await self.get_profiles(interaction, interaction.user.id)
        if len(profiles) == 1:
            id_, platform, username = profiles[0]
            embed = discord.Embed(color=self.bot.color(interaction.user.id))
            embed.title = "Are you sure you want to unlink the following profile?"
            embed.add_field(name="Platform", value=platform)
            embed.add_field(name="Username", value=username)

            if await self.bot.prompt(interaction, embed):
                await self.bot.pool.execute("DELETE FROM profile WHERE id = $1;", id_)
                await interaction.response.send_message("Profile successfully unlinked.")
        else:
            view = SelectProfilesView(profiles, author_id=interaction.user.id)
            message = "Select at least a profile to unlink..."
            view.message = await interaction.response.send_message(message, view=view)

    @has_profile()
    @profile.command()
    @app_commands.describe(member="The mention or the ID of a Discord member")
    async def ratings(self, interaction: discord.Interaction, member: None | discord.Member = None):
        """Provides SRs information for a profile"""
        await interaction.response.defer(thinking=True)
        member = member or interaction.user
        message = "Select a profile to view the skill ratings for."
        record = await self.select_profile(interaction, message, member)
        profile = Profile(interaction=interaction, record=record)
        await profile.compute_data()
        if profile.is_private():
            embed = profile.embed_private()
        else:
            embed = await profile.embed_ratings(save=True, profile_id=profile.id)
            # only update the nickname if the profile matches the one
            # selected for that purpose
            query = "SELECT * FROM nickname WHERE profile_id = $1;"
            flag = await self.bot.pool.fetchrow(query, profile.id)
            if flag and member.id == interaction.user.id:
                await Nickname(interaction, profile=profile).update()
        await interaction.followup.send(embed=embed)

    @has_profile()
    @profile.command()
    @app_commands.describe(member="The mention or the ID of a Discord member")
    async def stats(self, interaction: discord.Interaction, member: None | discord.Member = None):
        """Provides general stats for a profile"""
        await interaction.response.defer(thinking=True)
        member = member or interaction.user
        message = "Select a profile to view the stats for."
        _, platform, username = await self.select_profile(interaction, message, member)
        await interaction.client.get_cog("Stats").show_stats_for(
            interaction, "allHeroes", platform, username
        )

    @has_profile()
    @profile.command()
    @app_commands.autocomplete(hero=hero_autocomplete)
    @app_commands.describe(hero="The name of the hero to see stats for")
    @app_commands.describe(member="The mention or the ID of a Discord member")
    async def hero(
        self, interaction: discord.Interaction, hero: str, member: None | discord.Member = None
    ):
        """Provides general hero stats for a profile."""
        await interaction.response.defer(thinking=True)
        member = member or interaction.user
        message = f"Select a profile to view **{hero}** stats for."
        _, platform, username = await self.select_profile(interaction, message, member)
        await interaction.client.get_cog("Stats").show_stats_for(
            interaction, hero, platform, username
        )

    @has_profile()
    @profile.command()
    @app_commands.describe(member="The mention or the ID of a Discord member")
    async def summary(self, interaction: discord.Interaction, member: None | discord.Member = None):
        """Provides summarized stats for a profile"""
        await interaction.response.defer(thinking=True)
        member = member or interaction.user
        message = "Select a profile to view the summary for."
        record = await self.select_profile(interaction, message, member)
        profile = Profile(interaction=interaction, record=record)
        await profile.compute_data()
        if profile.is_private():
            embed = profile.embed_private()
        else:
            embed = profile.embed_summary()
        await interaction.followup.send(embed=embed)

    @has_profile()
    @profile.command()
    @app_commands.guild_only()
    @app_commands.checks.bot_has_permissions(manage_nicknames=True)
    async def nickname(self, interaction: discord.Interaction):
        """Shows or remove your SRs in your nickname

        The nickname can only be set in one server. It updates
        automatically whenever `profile rating` is used and the
        profile selected matches the one set for the nickname.
        """
        await interaction.response.defer(thinking=True)
        nick = Nickname(interaction)
        if not await nick.exists():
            if not await self.bot.prompt(
                interaction, "This will display your SRs in your nickname."
            ):
                return

            if interaction.guild.me.top_role < interaction.user.top_role:
                return await interaction.followup.send(
                    "This server's owner needs to move the `OverBot` role higher, so I will "
                    "be able to update your nickname. If you are this server's owner, there's "
                    "not way for me to change your nickname, sorry!"
                )

            message = "Select a profile to use for the nickname SRs."
            record = await self.select_profile(interaction, message)
            profile = Profile(interaction=interaction, record=record)

            if profile.is_private():
                return await interaction.followup.send(embed=profile.embed_private())

            nick.profile = profile

            try:
                await nick.set_or_remove(profile_id=profile.id)
            except Exception as e:
                await interaction.followup.send(e)
        else:
            if await self.bot.prompt(interaction, "This will remove your SR in your nickname."):
                try:
                    await nick.set_or_remove(remove=True)
                except Exception as e:
                    await interaction.followup.send(e)

    async def sr_graph(self, interaction: discord.Interaction, profile: Record):
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
            raise CannotCreateGraph()

        fig, ax = pyplot.subplots()
        ax.xaxis_date()

        sns.lineplot(data=data, ax=ax, linewidth=2.5)
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y-%m-%d"))
        fig.autofmt_xdate()

        fig.suptitle(f"{username} - {platform}", fontsize="20")
        pyplot.legend(title="Roles", loc="upper right")
        pyplot.xlabel("Date")
        pyplot.ylabel("SR")

        image = BytesIO()
        pyplot.savefig(format="png", fname=image, transparent=False)
        image.seek(0)

        file = discord.File(image, filename="graph.png")

        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar)
        embed.set_image(url="attachment://graph.png")
        return file, embed

    @is_premium()
    @has_profile()
    @profile.command(extras=dict(premium=True))
    async def graph(self, interaction: discord.Interaction):
        """Shows SRs performance graph."""
        message = "Select a profile to view the SRs graph for."
        profile = await self.select_profile(interaction, message)
        file, embed = await self.sr_graph(interaction, profile)
        await interaction.response.send_message(file=file, embed=embed)


async def setup(bot: OverBot):
    await bot.add_cog(ProfileCog(bot))
