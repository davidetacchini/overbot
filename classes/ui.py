from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord

from discord import ui

from utils import emojis
from utils.funcs import get_platform_emoji

if TYPE_CHECKING:
    from asyncpg import Record

PLATFORMS = [
    discord.SelectOption(label="Battle.net", value="pc", emoji=emojis.battlenet),
    discord.SelectOption(label="PlayStation", value="psn", emoji=emojis.psn),
    discord.SelectOption(label="XBOX", value="xbl", emoji=emojis.xbl),
    discord.SelectOption(label="Nintendo Switch", value="nintendo-switch", emoji=emojis.switch),
]


class ModalProfileLink(ui.Modal, title="Profile Link"):
    platform = ui.Select(placeholder="Select a platform...", options=PLATFORMS)
    username = ui.TextInput(
        label="Username",
        style=discord.TextStyle.short,
        placeholder="Enter your username",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
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
            self.profile = DropdownProfiles(profiles, placeholder="Select a profile...")
            self.add_item(self.profile)
        else:
            self.profile = profiles[0]
        self.platform = ui.Select(placeholder="Select a platform...", options=PLATFORMS)
        self.username = ui.TextInput(
            label="Username",
            style=discord.TextStyle.short,
            placeholder="Enter your username",
            required=True,
        )
        self.add_item(self.platform)
        self.add_item(self.username)

    async def on_submit(self, interaction: discord.Interaction):
        platform = self.platform.values[0]
        username = self.username.value

        try:
            profile_id, _, _ = self.profile
        except TypeError:
            profile_id = self.profile.values[0]

        query = "UPDATE profile SET platform = $1, username = $2 WHERE id = $3;"
        await interaction.client.pool.execute(query, platform, username, int(profile_id))
        await interaction.response.send_message("Profile successfully updated.", ephemeral=True)


class PromptView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__()
        self.author_id = author_id
        self.value: None | bool = None

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


class SelectView(discord.ui.View):
    def __init__(self, *, author_id: int, timeout: float = 120.0) -> None:
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.message: None | discord.Message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.author_id:
            return True
        await interaction.response.send_message(
            "This command was not initiated by you.", ephemeral=True
        )
        return False

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.delete()


class DropdownProfiles(discord.ui.Select):
    def __init__(self, profiles: list[Record], *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.profiles = profiles
        self.__fill_options()

    def __fill_options(self):
        for profile in self.profiles:
            id_, platform, username = profile
            emoji = get_platform_emoji(platform)
            self.add_option(label=f"{username}", value=id_, emoji=emoji)


class SelectProfileView(SelectView):
    def __init__(self, profiles: list[Record], *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        placeholder = "Select a profile..."
        self.select = DropdownProfiles(profiles, placeholder=placeholder)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red, row=1)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()


class SelectProfilesView(SelectView):
    def __init__(self, profiles: list[Record], *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.choices: list[int] = []
        placeholder = "Select a profile..."
        # Using min_values=0 to ensure that the view gets recomputed
        # even when the user deselect the previously selected profile(s).
        self.select = DropdownProfiles(
            profiles, min_values=0, max_values=len(profiles), placeholder=placeholder
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self.choices = list(map(int, self.select.values))

    @discord.ui.button(label="Unlink", style=discord.ButtonStyle.blurple, row=1)
    async def unlink(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.choices:
            await interaction.response.defer()
            await interaction.client.pool.execute(
                "DELETE FROM profile WHERE id = any($1::int[]);", self.choices
            )

            if len(self.choices) == 1:
                message = "Profile successfully unlinked."
            else:
                message = "Profiles successfully unlinked."

            await interaction.followup.send(message, ephemeral=True)
            self.stop()
        else:
            await interaction.response.send_message(
                "Please select at least a profile to unlink.", ephemeral=True
            )

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red, row=1)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()


class SelectAnswer(discord.ui.Select):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.view.stop()
