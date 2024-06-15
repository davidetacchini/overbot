from __future__ import annotations

from typing import Any, Mapping

import discord

from .paginator import Paginator


class BaseView(discord.ui.View):
    def __init__(
        self, *, interaction: discord.Interaction, timeout: float = 180.0, **kwargs: Any
    ) -> None:
        super().__init__(timeout=timeout, **kwargs)
        self.interaction = interaction
        self.message: None | discord.Message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.interaction.user.id:
            return True
        await interaction.response.send_message("This is not for you.", ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        try:
            if self.message:
                await self.message.delete()
            else:
                await self.interaction.delete_original_response()
        except Exception:
            pass


class PromptView(BaseView):
    def __init__(self, *, interaction: discord.Interaction) -> None:
        super().__init__(interaction=interaction)
        self.value: None | bool = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = True
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = False
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class PlatformSelect(discord.ui.Select):
    def __init__(self, entries: Mapping[str, discord.Embed | list[discord.Embed]] = {}) -> None:
        super().__init__(row=0, placeholder="Select a platform...")
        self.entries = entries
        self.add_option(label="PC", value="pc")
        self.add_option(label="Console", value="console")

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        value = self.values[0]
        await self.view.rebind(self.entries[value], interaction)


class PlatformSelectMenu(Paginator):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def add_platforms(self, platforms: Mapping[str, discord.Embed | list[discord.Embed]]) -> None:
        self.clear_items()
        self.add_item(PlatformSelect(entries=platforms))
        self.fill_items(force_quit=True)

    async def rebind(
        self, entries: discord.Embed | list[discord.Embed], interaction: discord.Interaction
    ) -> None:
        if isinstance(entries, discord.Embed):
            entries = [entries]
        self.entries = entries
        self.current = 0
        kwargs = self._get_kwargs_from_page(self.entries[0])
        self._update_labels(0)
        await interaction.response.edit_message(**kwargs, view=self)
