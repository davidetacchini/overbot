from __future__ import annotations

from typing import Any

import discord

from discord import ui

from utils import emojis
from utils.funcs import get_platform_emoji

from .profile import Profile

PLATFORMS = [
    discord.SelectOption(label="Battle.net", value="pc", emoji=emojis.battlenet),
    discord.SelectOption(label="PlayStation", value="psn", emoji=emojis.psn),
    discord.SelectOption(label="XBOX", value="xbl", emoji=emojis.xbl),
    discord.SelectOption(label="Nintendo Switch", value="nintendo-switch", emoji=emojis.switch),
]


class ModalProfileLink(ui.Modal, title="Profile Link"):
    platform: ui.Select = ui.Select(placeholder="Select a platform...", options=PLATFORMS)
    username: ui.TextInput = ui.TextInput(
        label="Username",
        style=discord.TextStyle.short,
        placeholder="Enter your username",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        bot: Any = interaction.client
        platform = self.platform.values[0]
        username = self.username.value

        query = "INSERT INTO profile (platform, username, member_id) VALUES ($1, $2, $3);"
        await bot.pool.execute(query, platform, username, interaction.user.id)
        await interaction.response.send_message("Profile successfully linked.", ephemeral=True)


class ModalProfileUpdate(ui.Modal, title="Profile Update"):
    def __init__(self, profiles: list[Profile]) -> None:
        super().__init__()
        self.profiles = profiles
        if len(profiles) > 1:
            self.profile: DropdownProfiles | Profile = DropdownProfiles(
                profiles, placeholder="Select a profile..."
            )
            self.add_item(self.profile)
        else:
            self.profile = profiles[0]
        self.platform: ui.Select = ui.Select(placeholder="Select a platform...", options=PLATFORMS)
        self.username: ui.TextInput = ui.TextInput(
            label="Username",
            style=discord.TextStyle.short,
            placeholder="Enter your username",
            required=True,
        )
        self.add_item(self.platform)
        self.add_item(self.username)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        bot: Any = interaction.client
        new_platform = self.platform.values[0]
        new_username = self.username.value

        if isinstance(self.profile, Profile):
            profile_id = self.profile.id
        else:
            profile_id = int(self.profile.values[0])

        query = "UPDATE profile SET platform = $1, username = $2 WHERE id = $3;"
        await bot.pool.execute(query, new_platform, new_username, profile_id)
        await interaction.response.send_message("Profile successfully updated.", ephemeral=True)


class BaseView(discord.ui.View):
    def __init__(
        self, *, interaction: discord.Interaction, timeout: float = 120.0, **kwargs: Any
    ) -> None:
        super().__init__(timeout=timeout, **kwargs)
        self.interaction = interaction
        self.author_id = interaction.user.id
        self.message: None | discord.Message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.author_id:
            return True
        await interaction.response.send_message(
            "This command wes not initiated by you.", ephemeral=True
        )
        return False

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.delete()
        else:
            await self.interaction.delete_original_message()


class PromptView(BaseView):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.value: None | bool = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = True
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = False
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()


class DropdownProfiles(discord.ui.Select):
    def __init__(self, profiles: list[Profile], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.profiles = profiles
        self.__fill_options()

    def __fill_options(self) -> None:
        for profile in self.profiles:
            emoji = get_platform_emoji(profile.platform)
            self.add_option(label=profile.username, value=str(profile.id), emoji=emoji)


class SelectProfileView(BaseView):
    def __init__(self, profiles: list[Profile], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        placeholder = "Select a profile..."
        self.select = DropdownProfiles(profiles, placeholder=placeholder)
        setattr(self.select, "callback", self.select_callback)
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


class UnlinkProfilesView(BaseView):
    def __init__(self, profiles: list[Profile], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.choices: list[int] = []
        placeholder = "Select at least a profile..."
        # Using min_values=0 to ensure that the view gets recomputed
        # even when the user unselects the previously selected profile(s).
        self.select = DropdownProfiles(
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
            bot: Any = interaction.client
            await bot.pool.execute("DELETE FROM profile WHERE id = any($1::int[]);", self.choices)

            if len(self.choices) == 1:
                message = "Profile successfully unlinked."
            else:
                message = "Profiles successfully unlinked."

            await interaction.delete_original_message()
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
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.view.stop()
