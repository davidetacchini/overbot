from __future__ import annotations

import logging

from typing import TYPE_CHECKING

import discord

from discord import app_commands
from discord.ext import commands
from discord.app_commands import Choice

from classes.ui import ProfileUnlinkView, SelectProfileView
from utils.checks import has_profile, can_add_profile, subcommand_guild_only
from utils.helpers import (
    platform_choices,
    hero_autocomplete,
    get_platform_emoji,
    profile_autocomplete,
)
from classes.profile import Profile
from classes.nickname import Nickname
from classes.exceptions import NoChoice, ProfileNotLinked

if TYPE_CHECKING:
    from bot import OverBot

Member = discord.User | discord.Member

log = logging.getLogger("overbot")


# Workaround for checks not working properly in Context Menus. To clarify: has_profile does not work,
# @app_commands.checks does. However, Interaction.namespace returns an empty Namespace for Context Menus,
# and has_profile uses Interaction.namespace to check whether it's the author whose profiles needs to be
# fetched. Interaction.data (didn't tried that for Context Menus, but should work) can be used
# instead of Interaction.namespace but I prefer this workaround for now.
async def cm_has_profiles(interaction: discord.Interaction, member_id: int) -> bool:
    """Custom check for Context Menus."""
    query = """SELECT platform, username
               FROM profile
               INNER JOIN member
                       ON member.id = profile.member_id
               WHERE member.id = $1;
            """
    if not await interaction.client.pool.fetch(query, member_id):
        raise ProfileNotLinked(is_author=member_id == interaction.user.id)


@app_commands.context_menu(name="List Profiles")
async def list_profiles(interaction: discord.Interaction, member: discord.Member) -> None:
    """List your own or a member's profiles"""
    profile_cog = interaction.client.get_cog("Profile")
    profiles = await profile_cog.get_profiles(interaction, member.id)
    entries = await profile_cog.list_profiles(interaction, member, profiles)
    await interaction.client.paginate(entries, interaction=interaction)


@app_commands.context_menu(name="Show Ratings")
async def show_ratings(interaction: discord.Interaction, member: discord.Member) -> None:
    """Provides SRs information for a profile"""
    await interaction.response.defer(thinking=True)
    await cm_has_profiles(interaction, member.id)
    message = "Select a profile to view the skill ratings for:"
    profile = await interaction.client.get_cog("Profile").select_profile(
        interaction, message, member
    )
    await profile.compute_data()
    if profile.is_private():
        embed = profile.embed_private()
    else:
        embed = await profile.embed_ratings(save=True, profile_id=profile.id)
    await interaction.followup.send(embed=embed)


@app_commands.context_menu(name="Show Stats")
async def show_stats(interaction: discord.Interaction, member: discord.Member) -> None:
    """Provides general stats for a profile"""
    await interaction.response.defer(thinking=True)
    await cm_has_profiles(interaction, member.id)
    message = "Select a profile to view the stats for:"
    profile = await interaction.client.get_cog("Profile").select_profile(
        interaction, message, member
    )
    await interaction.client.get_cog("Stats").show_stats_for(
        interaction, "all-heroes", profile=profile
    )


@app_commands.context_menu(name="Show Summary")
async def show_summary(interaction: discord.Interaction, member: discord.Member) -> None:
    """Provides summarized stats for a profile"""
    await interaction.response.defer(thinking=True)
    await cm_has_profiles(interaction, member.id)
    message = "Select a profile to view the summary for:"
    profile = await interaction.client.get_cog("Profile").select_profile(
        interaction, message, member
    )
    await profile.compute_data()
    if profile.is_private():
        embed = profile.embed_private()
    else:
        embed = profile.embed_summary()
    await interaction.followup.send(embed=embed)


class ProfileCog(commands.Cog, name="Profile"):
    def __init__(self, bot: OverBot) -> None:
        self.bot = bot

    profile = app_commands.Group(name="profile", description="Manage your Overwatch profiles")

    async def get_profiles(self, interaction: discord.Interaction, member_id: int) -> list[Profile]:
        limit = self.bot.get_profiles_limit(interaction, member_id)
        query = """SELECT profile.id, platform, username
                   FROM profile
                   INNER JOIN member
                           ON member.id = profile.member_id
                   WHERE member.id = $1
                   LIMIT $2;
                """
        records = await self.bot.pool.fetch(query, member_id, limit)
        return [Profile(interaction=interaction, record=r) for r in records]

    async def select_profile(
        self, interaction: discord.Interaction, message: str, member: None | Member = None
    ) -> Profile:
        member = member or interaction.user
        profiles = await self.get_profiles(interaction, member.id)

        # if there only is a profile: just return it
        if len(profiles) == 1:
            return profiles[0]

        view = SelectProfileView(profiles, interaction=interaction)
        # Using defer() on every single command that calls 'select_profile'.
        # Thus, the interaction is always responded and we can use
        # followup.send to respond.
        view.message = await interaction.followup.send(message, view=view)
        await view.wait()

        choice = view.select.values[0] if len(view.select.values) else None

        if choice is not None:
            for profile in profiles:
                if profile.id == int(choice):
                    return profile
        raise NoChoice() from None

    async def list_profiles(
        self, interaction: discord.Interaction, member: Member, profiles: list[Profile]
    ) -> discord.Embed | list[discord.Embed]:
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.set_author(name=member, icon_url=member.display_avatar)

        if not profiles:
            embed.description = "No profiles..."
            embed.set_footer(text=f"Requested by {interaction.user}")
            return embed

        # using iter(profiles) because as_chunks accepts an iterator as its first parameter
        chunks = [c for c in discord.utils.as_chunks(iter(profiles), 10)]
        limit = self.bot.get_profiles_limit(interaction, member.id)

        pages = []
        for chunk in chunks:
            embed = embed.copy()
            embed.set_footer(
                text=f"{len(profiles)}/{limit} profiles • Requested by {interaction.user}"
            )
            description = []
            for profile in chunk:
                description.append(f"{get_platform_emoji(profile.platform)} {profile.username}")
            embed.description = "\n".join(description)
            pages.append(embed)
        return pages

    @profile.command()
    @app_commands.describe(member="The member to list the profiles for")
    async def list(self, interaction: discord.Interaction, member: None | Member = None) -> None:
        """List your own or a member's profiles"""
        member = member or interaction.user
        profiles = await self.get_profiles(interaction, member.id)
        entries = await self.list_profiles(interaction, member, profiles)
        await self.bot.paginate(entries, interaction=interaction)

    @profile.command()
    @app_commands.choices(platform=platform_choices)
    @app_commands.describe(platform="The platform of the profile")
    @app_commands.describe(username="The username of the profile")
    @can_add_profile()
    async def link(
        self, interaction: discord.Interaction, platform: Choice[str], username: str
    ) -> None:
        """Link an Overwatch profile"""
        # Make sure the member is in the member table. If a new member runs this command as the first
        # command, it won't be in the member table and this could lead to a ForeignKeyViolationError.
        await self.bot.insert_member(interaction.user.id)
        query = "INSERT INTO profile (platform, username, member_id) VALUES ($1, $2, $3);"
        try:
            await self.bot.pool.execute(query, platform.value, username, interaction.user.id)
        except Exception:
            await interaction.response.send_message(
                "Something bad happened while linking the profile."
            )
        else:
            await interaction.response.send_message("Profile successfully linked.", ephemeral=True)

    @profile.command()
    @app_commands.choices(platform=platform_choices)
    @app_commands.autocomplete(profile=profile_autocomplete)
    @app_commands.describe(profile="The profile to update")
    @app_commands.describe(platform="The new profile platform")
    @app_commands.describe(username="The new profile username")
    @has_profile()
    async def update(
        self, interaction: discord.Interaction, profile: int, platform: Choice[str], username: str
    ) -> None:
        """Update an Overwatch profile"""
        query = "UPDATE profile SET platform = $1, username = $2 WHERE id = $3;"
        try:
            await self.bot.pool.execute(query, platform.value, username, profile)
        except Exception:
            await interaction.response.send_message(
                "Something bad happened while updating the profile."
            )
        else:
            await interaction.response.send_message("Profile successfully updated.", ephemeral=True)

    @profile.command()
    @has_profile()
    async def unlink(self, interaction: discord.Interaction) -> None:
        """Unlink an Overwatch profile"""
        profiles = await self.get_profiles(interaction, interaction.user.id)
        if len(profiles) == 1:
            profile = profiles[0]
            embed = discord.Embed(color=self.bot.color(interaction.user.id))
            embed.title = "Are you sure you want to unlink the following profile?"
            embed.add_field(name="Platform", value=profile.platform)
            embed.add_field(name="Username", value=profile.username)

            if await self.bot.prompt(interaction, embed):
                await self.bot.pool.execute("DELETE FROM profile WHERE id = $1;", profile.id)
                await interaction.followup.send("Profile successfully unlinked.", ephemeral=True)
        else:
            view = ProfileUnlinkView(profiles, interaction=interaction)
            message = "Select at least a profile to unlink:"
            await interaction.response.send_message(message, view=view)

    @profile.command()
    @app_commands.describe(member="The member to show ratings for")
    @has_profile()
    async def ratings(self, interaction: discord.Interaction, member: None | Member = None) -> None:
        """Provides SRs information for a profile"""
        await interaction.response.defer(thinking=True)
        member = member or interaction.user
        message = "Select a profile to view the skill ratings for:"
        profile = await self.select_profile(interaction, message, member)
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

    @profile.command()
    @app_commands.describe(member="The member to show stats for")
    @has_profile()
    async def stats(self, interaction: discord.Interaction, member: None | Member = None) -> None:
        """Provides general stats for a profile"""
        await interaction.response.defer(thinking=True)
        member = member or interaction.user
        message = "Select a profile to view the stats for:"
        profile = await self.select_profile(interaction, message, member)
        await self.bot.get_cog("Stats").show_stats_for(interaction, "all-heroes", profile=profile)

    @profile.command()
    @app_commands.autocomplete(hero=hero_autocomplete)
    @app_commands.describe(hero="The name of the hero to see stats for")
    @app_commands.describe(member="The member to show hero stats for")
    @has_profile()
    async def hero(
        self, interaction: discord.Interaction, hero: str, member: None | Member = None
    ) -> None:
        """Provides general hero stats for a profile"""
        await interaction.response.defer(thinking=True)
        member = member or interaction.user
        message = f"Select a profile to view **{hero}** stats for:"
        profile = await self.select_profile(interaction, message, member)
        await self.bot.get_cog("Stats").show_stats_for(interaction, hero, profile=profile)

    @profile.command()
    @app_commands.describe(member="The member to show the summary for")
    @has_profile()
    async def summary(self, interaction: discord.Interaction, member: None | Member = None) -> None:
        """Provides summarized stats for a profile"""
        await interaction.response.defer(thinking=True)
        member = member or interaction.user
        message = "Select a profile to view the summary for:"
        profile = await self.select_profile(interaction, message, member)
        await profile.compute_data()
        if profile.is_private():
            embed = profile.embed_private()
        else:
            embed = profile.embed_summary()
        await interaction.followup.send(embed=embed)

    @profile.command()
    @app_commands.checks.bot_has_permissions(manage_nicknames=True)
    @has_profile()
    @app_commands.guild_only()
    @subcommand_guild_only()
    async def nickname(self, interaction: discord.Interaction) -> None:
        """Shows or remove your SRs in your nickname

        The nickname can only be set in one server. It updates
        automatically whenever `profile rating` is used and the
        profile selected matches the one set for the nickname.
        """
        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        user = interaction.user
        if guild.me.top_role < user.top_role or user.id == guild.owner_id:
            return await interaction.followup.send(
                "This server's owner needs to move the `OverBot` role higher, so I will "
                "be able to update your nickname. If you are this server's owner, there's "
                "no way for me to change your nickname, sorry!"
            )

        nick = Nickname(interaction)
        if await nick.exists():
            if await self.bot.prompt(interaction, "This will remove your SRs in your nickname."):
                try:
                    await nick.set_or_remove(remove=True)
                except Exception as e:
                    await interaction.followup.send(str(e))
            return

        if not await self.bot.prompt(interaction, "This will display your SRs in your nickname."):
            return

        message = "Select a profile to use for the nickname SRs:"
        profile = await self.select_profile(interaction, message)
        await profile.compute_data()

        if profile.is_private():
            return await interaction.followup.send(embed=profile.embed_private())

        nick.profile = profile

        try:
            await nick.set_or_remove(profile_id=profile.id)
        except Exception as e:
            await interaction.followup.send(str(e))


async def setup(bot: OverBot) -> None:
    context_menus = (list_profiles, show_ratings, show_stats, show_summary)
    for command in context_menus:
        setattr(command, "__cog_name__", "Profile")
        bot.tree.add_command(command)
    await bot.add_cog(ProfileCog(bot))
