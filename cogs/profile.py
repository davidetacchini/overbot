from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

from classes.exceptions import NoChoice
from classes.profile import Profile
from classes.ui import BaseView, PlatformSelectMenu
from utils.checks import can_add_profile, has_profile
from utils.helpers import hero_autocomplete, profile_autocomplete

if TYPE_CHECKING:
    from bot import OverBot

    from .stats import Stats

Member = discord.User | discord.Member

log = logging.getLogger(__name__)


DEFAULT_PROFILES_LIMIT = 5
PREMIUM_PROFILES_LIMIT = 25


class ProfileSelect(discord.ui.Select):
    def __init__(self, profiles: list[Profile], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.profiles = profiles
        self.__fill_options()

    def __fill_options(self) -> None:
        for profile in self.profiles:
            self.add_option(label=profile.battletag, value=str(profile.id))  # type: ignore


class ProfileSelectView(BaseView):
    def __init__(self, profiles: list[Profile], *, interaction: discord.Interaction) -> None:
        super().__init__(interaction=interaction)
        placeholder = f"Select a profile... ({len(profiles)} found)"
        self.select = ProfileSelect(profiles, placeholder=placeholder)
        setattr(self.select, "callback", self.select_callback)
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red, row=1)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class ProfileUnlinkView(BaseView):
    def __init__(self, profiles: list[Profile], *, interaction: discord.Interaction) -> None:
        super().__init__(interaction=interaction)
        self.bot: OverBot = getattr(interaction, "client")
        self.choices: list[int] = []
        placeholder = "Select at least a profile..."
        # Using min_values=0 to ensure that the view gets recomputed
        # even when the user unselects the previously selected profile(s).
        self.select = ProfileSelect(
            profiles, min_values=0, max_values=len(profiles), placeholder=placeholder
        )
        setattr(self.select, "callback", self.select_callback)
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self.choices = list(map(int, self.select.values))

    @discord.ui.button(label="Unlink", style=discord.ButtonStyle.blurple, row=1)
    async def unlink(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.choices:
            await interaction.response.defer()
            await self.bot.pool.execute(
                "DELETE FROM profile WHERE id = any($1::int[]);", self.choices
            )

            if len(self.choices) == 1:
                message = "Profile successfully unlinked."
            else:
                message = "Profiles successfully unlinked."

            await interaction.delete_original_response()
            await interaction.followup.send(message, ephemeral=True)
            self.stop()
        else:
            await interaction.response.send_message(
                "Please select at least a profile to unlink.", ephemeral=True
            )

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red, row=1)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


@app_commands.context_menu(name="List Profiles")
async def list_profiles(interaction: discord.Interaction, member: discord.Member) -> None:
    """Lists your own or a member's profiles."""
    bot: OverBot = getattr(interaction, "client")
    profile_cog: ProfileCog = bot.get_cog("profile")  # type: ignore
    profiles = await profile_cog.get_profiles(interaction, member.id)
    entries = await profile_cog.list_profiles(interaction, member, profiles)
    await bot.paginate(entries, interaction=interaction)


class ProfileCog(commands.GroupCog, name="profile"):
    def __init__(self, bot: OverBot) -> None:
        self.bot = bot
        super().__init__()

    def get_profiles_limit(self, interaction: discord.Interaction, user_id: int) -> int:
        guild_id = interaction.guild_id or 0
        if not self.bot.is_it_premium(user_id, guild_id):
            return DEFAULT_PROFILES_LIMIT
        return PREMIUM_PROFILES_LIMIT

    async def get_profiles(self, interaction: discord.Interaction, member_id: int) -> list[Profile]:
        limit = self.get_profiles_limit(interaction, member_id)
        query = """SELECT profile.id, battletag
                   FROM profile
                   INNER JOIN member
                           ON member.id = profile.member_id
                   WHERE member.id = $1
                   ORDER BY battletag
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

        view = ProfileSelectView(profiles, interaction=interaction)
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
        embed.set_author(name=member.display_name, icon_url=member.display_avatar)

        if not profiles:
            embed.description = "No profiles."
            embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            return embed

        # using iter(profiles) because as_chunks accepts an iterator as its first parameter
        chunks = [c for c in discord.utils.as_chunks(iter(profiles), 10)]
        limit = self.get_profiles_limit(interaction, member.id)

        pages = []
        for chunk in chunks:
            embed = embed.copy()
            embed.set_footer(
                text=f"{len(profiles)}/{limit} profiles • Requested by {interaction.user.display_name}"
            )
            description = []
            for index, profile in enumerate(chunk, start=1):
                description.append(f"{index}. {profile.battletag}")
            embed.description = "\n".join(description)
            pages.append(embed)
        return pages

    @app_commands.command()
    @app_commands.describe(member="The member to list the profiles for")
    async def list(self, interaction: discord.Interaction, member: None | Member = None) -> None:
        """Lists your own or a member's profiles."""
        member = member or interaction.user
        profiles = await self.get_profiles(interaction, member.id)
        entries = await self.list_profiles(interaction, member, profiles)
        await self.bot.paginate(entries, interaction=interaction)

    @app_commands.command()
    @app_commands.describe(battletag="The battletag of the profile")
    @can_add_profile()
    async def link(self, interaction: discord.Interaction, battletag: str) -> None:
        """Link an Overwatch profile."""
        # Make sure the member is in the member table. If a new member runs this command as the first
        # command, it won't be in the member table and this could lead to a ForeignKeyViolationError.
        await self.bot.insert_member(interaction.user.id)
        query = "INSERT INTO profile (battletag, member_id) VALUES ($1, $2);"
        try:
            await self.bot.pool.execute(query, battletag, interaction.user.id)
        except Exception:
            await interaction.response.send_message(
                "Something bad happened while linking the profile."
            )
        else:
            await interaction.response.send_message("Profile successfully linked.", ephemeral=True)

    @app_commands.command()
    @app_commands.autocomplete(profile=profile_autocomplete)
    @app_commands.describe(profile="The profile to update")
    @app_commands.describe(battletag="The new profile battletag")
    @has_profile()
    async def update(self, interaction: discord.Interaction, profile: int, battletag: str) -> None:
        """Update an Overwatch profile."""
        query = "UPDATE profile SET battletag = $1 WHERE id = $2;"
        try:
            await self.bot.pool.execute(query, battletag, profile)
        except Exception:
            await interaction.response.send_message(
                "Something bad happened while updating the profile."
            )
        else:
            await interaction.response.send_message("Profile successfully updated.", ephemeral=True)

    @app_commands.command()
    @has_profile()
    async def unlink(self, interaction: discord.Interaction) -> None:
        """Unlink an Overwatch profile."""
        profiles = await self.get_profiles(interaction, interaction.user.id)
        if len(profiles) == 1:
            profile = profiles[0]
            embed = discord.Embed(color=self.bot.color(interaction.user.id))
            embed.title = "Are you sure you want to unlink the following profile?"
            embed.add_field(name="BattleTag", value=profile.battletag)

            if await self.bot.prompt(interaction, embed):
                await self.bot.pool.execute("DELETE FROM profile WHERE id = $1;", profile.id)
                await interaction.followup.send("Profile successfully unlinked.", ephemeral=True)
        else:
            view = ProfileUnlinkView(profiles, interaction=interaction)
            message = "Select at least a profile to unlink:"
            await interaction.response.send_message(message, view=view)

    @app_commands.command()
    @app_commands.describe(member="The member to show ratings for")
    @has_profile()
    async def ratings(self, interaction: discord.Interaction, member: None | Member = None) -> None:
        """Provides SRs information for a profile."""
        await interaction.response.defer(thinking=True)
        member = member or interaction.user
        message = "Select a profile to view the skill ratings for:"
        profile = await self.select_profile(interaction, message, member)
        await profile.fetch_data()

        if profile.is_private():
            embed = profile.embed_private()
            await interaction.followup.send(embed=embed)
            return

        data = profile.embed_ratings()
        value = "console" if not data["pc"] else "pc"
        view = PlatformSelectMenu(data[value], interaction=interaction)
        view.add_platforms(data)
        await view.start()

    @app_commands.command()
    @app_commands.autocomplete(hero=hero_autocomplete)
    @app_commands.describe(
        hero="The hero name to see the stats for. If not given then it shows general stats"
    )
    @app_commands.describe(member="The member to show stats for")
    @has_profile()
    async def stats(
        self,
        interaction: discord.Interaction,
        hero: str = "all-heroes",
        member: None | Member = None,
    ) -> None:
        """Provides general stats or hero specific stats for a profile."""
        await interaction.response.defer(thinking=True)
        member = member or interaction.user
        if hero == "all-heroes":
            message = "Select a profile to view the stats for:"
        else:
            message = f"Select a profile to view **{hero}** stats for:"
        profile = await self.select_profile(interaction, message, member)
        stats_cog: Stats = self.bot.get_cog("Stats")  # type: ignore
        await stats_cog.show_stats_for(interaction, hero, profile=profile)

    def cog_unload(self):
        self.bot.tree.remove_command(list_profiles.name, type=list_profiles.type)

    @app_commands.command()
    @app_commands.describe(member="The member to show summary for")
    @has_profile()
    async def summary(self, interaction: discord.Interaction, member: None | Member = None) -> None:
        """Provides summarized stats for a profile.

        Data from both competitive and quickplay, and/or pc and console is merged.
        """
        await interaction.response.defer(thinking=True)
        member = member or interaction.user
        message = "Select a profile to view the summary for:"
        profile = await self.select_profile(interaction, message, member)
        await profile.fetch_data()

        if profile.is_private():
            embed = profile.embed_private()
        else:
            embed = await profile.embed_summary()

        await interaction.followup.send(embed=embed)


async def setup(bot: OverBot) -> None:
    setattr(list_profiles, "__cog_name__", "profile")
    bot.tree.add_command(list_profiles)
    await bot.add_cog(ProfileCog(bot))
