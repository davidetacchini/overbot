from typing import Any, Sequence

import discord

from utils import emojis


class Paginator(discord.ui.View):
    def __init__(
        self,
        entries: discord.Embed | str | Sequence[discord.Embed | str],
        *,
        interaction: discord.Interaction,
        **kwargs: Any
    ) -> None:
        super().__init__(timeout=120.0, **kwargs)
        if isinstance(entries, (discord.Embed, str)):
            entries = [entries]

        self.entries = entries
        self.interaction = interaction
        self.current: int = 0
        self.message: None | discord.Message = None
        self.clear_items()
        self.fill_items()

    @property
    def max_pages(self) -> int:
        return len(self.entries) - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.interaction.user.id:
            return True
        await interaction.response.send_message("This is not for you.", ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        try:
            if self.message:
                await self.message.edit(view=None)
            else:
                await self.interaction.edit_original_response(view=None)
        except Exception:
            pass

    def fill_items(self, *, force_quit: bool = False) -> None:
        if self.max_pages >= 2:
            self.add_item(self.first)
        if self.max_pages > 0:
            self.add_item(self.previous)
            self.add_item(self.next)
        if self.max_pages >= 2:
            self.add_item(self.last)
        if self.max_pages > 0 or force_quit:
            self.add_item(self.quit_session)

    def _update_labels(self, page: int) -> None:
        self.first.disabled = self.previous.disabled = page == 0
        self.last.disabled = self.next.disabled = page == self.max_pages

    def _get_kwargs_from_page(self, page: str | dict | discord.Embed) -> dict[str, Any]:
        if isinstance(page, dict):
            return page
        elif isinstance(page, discord.Embed):
            return {"content": None, "embed": page}
        elif isinstance(page, str):
            return {"content": page, "embed": None}

    async def _update(self, interaction: discord.Interaction) -> None:
        kwargs = self._get_kwargs_from_page(self.entries[self.current])
        self._update_labels(self.current)
        if kwargs:
            if interaction.response.is_done():
                if self.message:
                    await self.message.edit(**kwargs, view=self)
            else:
                await interaction.response.edit_message(**kwargs, view=self)

    async def start(self) -> None:
        kwargs = self._get_kwargs_from_page(self.entries[0])
        self._update_labels(0)
        if self.interaction.response.is_done():
            self.message = await self.interaction.followup.send(**kwargs, view=self)
        else:
            await self.interaction.response.send_message(**kwargs, view=self)

    @discord.ui.button(emoji=emojis.left_d_caret, style=discord.ButtonStyle.blurple)
    async def first(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.current > 0:
            self.current = 0
            await self._update(interaction)

    @discord.ui.button(emoji=emojis.left_caret, style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.current - 1 >= 0:
            self.current -= 1
            await self._update(interaction)

    @discord.ui.button(emoji=emojis.right_caret, style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.current + 1 <= self.max_pages:
            self.current += 1
            await self._update(interaction)

    @discord.ui.button(emoji=emojis.right_d_caret, style=discord.ButtonStyle.blurple)
    async def last(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.current < self.max_pages:
            self.current = self.max_pages
            await self._update(interaction)

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red)
    async def quit_session(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()
