from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from discord import ui

from utils import emojis
from utils.funcs import get_platform_emoji

from .exceptions import NoChoice

if TYPE_CHECKING:
    from asyncpg import Record

PLATFORMS = [
    discord.SelectOption(label="Battle.net", value="pc", emoji=emojis.battlenet),
    discord.SelectOption(label="PlayStation", value="psn", emoji=emojis.psn),
    discord.SelectOption(label="XBOX", value="xbl", emoji=emojis.xbl),
    discord.SelectOption(label="Nintendo Switch", value="nintendo-switch", emoji=emojis.switch),
]


class ModalProfileLink(ui.Modal, title="Profile Link"):
    platform = ui.Select(placeholder="Select a platform", options=PLATFORMS)
    username = ui.TextInput(
        label="Username",
        style=discord.TextStyle.short,
        placeholder="Enter your username",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.platform == "pc":
            self.username = self.username.replace("-", "#")

        platform = self.platform.values[0]
        username = self.username.value

        query = "INSERT INTO profile (platform, username, member_id) VALUES ($1, $2, $3);"
        await interaction.client.pool.execute(query, platform, username, interaction.user.id)
        await interaction.response.send_message("Profile successfully linked.", ephemeral=True)


class ModalProfileUpdate(ui.Modal, title="Profile Update"):
    def __init__(self, profiles: list[Record]):
        super().__init__()
        self.profiles = profiles
        if len(profiles) > 1:
            self.profile = SelectProfile(profiles)
            self.add_item(self.profile)
        else:
            self.profile = profiles[0]
        self.platform = ui.Select(placeholder="Select a platform", options=PLATFORMS)
        self.username = ui.TextInput(
            label="Username",
            style=discord.TextStyle.short,
            placeholder="Enter your username",
            required=True,
        )
        self.add_item(self.platform)
        self.add_item(self.username)

    async def on_submit(self, interaction: discord.Interaction):
        if self.platform == "pc":
            self.username = self.username.replace("-", "#")

        platform = self.platform.values[0]
        username = self.username.value
        try:
            profile_id, _, _ = self.profile
        except TypeError:
            profile_id = self.profile.values[0]

        query = "UPDATE profile SET platform = $1, username = $2 WHERE id = $3;"
        await interaction.client.pool.execute(query, platform, username, int(profile_id))
        await interaction.response.send_message("Profile successfully updated.", ephemeral=True)


class Prompt(discord.ui.View):
    def __init__(self, author_id):
        super().__init__()
        self.author_id = author_id
        self.value = None

    async def interaction_check(self, interaction):
        if interaction.user and interaction.user.id == self.author_id:
            return True
        await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
        return False

    async def on_timeout(self):
        if self.message:
            await self.message.delete()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()


class SelectBase(discord.ui.Select):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.view.stop()


class SelectView(discord.ui.View):
    def __init__(
        self,
        entries: None | list[str] = None,
        *,
        interaction: discord.Interaction,
        timeout: float = 120.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.entries = entries
        self.interaction = interaction
        self.message: None | discord.Message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.interaction.user.id:
            return True
        await interaction.response.send_message(
            "This command was not initiated by you.", ephemeral=True
        )
        return False

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.delete()


class SelectProfileView(SelectView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # TODO: avoid NoChoice raising when quitting
    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red, row=1)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()


class SelectProfile(SelectBase):
    def __init__(self, profiles: list[Record]):
        super().__init__(placeholder="Select a profile...")
        self.profiles = profiles
        self.__fill_options()

    def __fill_options(self):
        for profile in self.profiles:
            id_, platform, username = profile
            emoji = get_platform_emoji(platform)
            self.add_option(label=f"{username}", value=id_, emoji=emoji)


async def select_profile(
    interaction: discord.Interaction, message: str, member: None | discord.Member = None
) -> str:
    member = member or interaction.user
    profiles = await interaction.client.get_cog("Profile").get_profiles(interaction, member)

    # if there only is a profile then just return it
    if len(profiles) == 1:
        profile_id, _, _ = profiles[0]
        return await interaction.client.get_cog("Profile").get_profile(profile_id)

    view = SelectProfileView(interaction=interaction)
    select = SelectProfile(profiles)
    view.add_item(select)

    if interaction.response.is_done():
        view.message = await interaction.followup.send(message, view=view)
    else:
        view.message = await interaction.response.send_message(message, view=view)
    await view.wait()

    choice = select.values[0] if len(select.values) else None

    if choice is not None:
        return await interaction.client.get_cog("Profile").get_profile(choice)
    raise NoChoice() from None


async def select_answer(
    entries: list[str | discord.Embed],
    *,
    interaction: discord.Interaction,
    timeout: float,
    embed: discord.Embed,
) -> str:
    view = SelectView(entries, interaction=interaction, timeout=timeout)
    select = SelectBase(placeholder="Select the correct answer...")
    view.add_item(select)

    embed.description = ""
    for index, entry in enumerate(entries, start=1):
        select.add_option(label=entry)
        embed.description = f"{embed.description}{index}. {entry}\n"

    view.message = await interaction.response.send_message(embed=embed, view=view)
    await view.wait()

    if (choice := select.values[0]) is not None:
        return choice
    raise NoChoice()
