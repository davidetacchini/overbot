from typing import Union, Optional

import discord

from utils import emojis
from classes.context import Context

from .exceptions import NoChoice


class Paginator(discord.ui.View):
    def __init__(self, entries: list[Union[discord.Embed, str]], *, ctx: "Context", **kwargs):
        super().__init__(**kwargs)
        self.entries = entries
        self.ctx = ctx
        self.current = 0
        self.total = len(self.entries) - 1
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user and interaction.user.id == self.ctx.author.id:
            return True
        await interaction.response.send_message(
            "This command was not initiated by you.", ephemeral=True
        )
        return False

    async def on_timeout(self):
        if self.message:
            await self.message.delete()

    def fill_items():
        pass

    def update_labels():
        pass

    async def start(self):
        self.message = await self.ctx.send(embed=self.entries[0], view=self)

    async def update(self, page):
        await self.message.edit(embed=self.entries[page])

    @discord.ui.button(label="<<", style=discord.ButtonStyle.blurple)
    async def first(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current > 0:
            self.current = 0
            await self.update(self.current)

    @discord.ui.button(label="<", style=discord.ButtonStyle.blurple)
    async def previous(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current - 1 >= 0:
            self.current -= 1
            await self.update(self.current)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.red)
    async def stop_session(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()

    @discord.ui.button(label=">", style=discord.ButtonStyle.blurple)
    async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current + 1 < self.total:
            self.current += 1
            await self.update(self.current)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.blurple)
    async def last(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current < self.total:
            self.current = self.total
            await self.update(self.current)


class ChooseSelect(discord.ui.Select):
    async def callback(self, interaction: discord.Interaction):
        self.view.choice = self.values[0]
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.view.stop()


class ChooseView(discord.ui.View):
    def __init__(
        self,
        entries: Optional[list[str]] = None,
        *,
        ctx: "Context",
        timeout: float = 120.0,
    ):
        super().__init__(timeout=timeout)
        self.entries = entries
        self.ctx = ctx
        self.choice: Optional[str] = None
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user and interaction.user.id == self.ctx.author.id:
            return True
        await interaction.response.send_message(
            "This command was not initiated by you.", ephemeral=True
        )
        return False

    async def on_timeout(self):
        if self.message:
            await self.message.delete()


async def choose_answer(entries, *, ctx, timeout, embed):
    view = ChooseView(entries, ctx=ctx, timeout=timeout)
    select = ChooseSelect(placeholder="Select the correct answer...")
    view.add_item(select)

    for index, entry in enumerate(entries, start=1):
        select.add_option(label=entry)
        embed.description = f"{embed.description}{index}. {entry}\n"

    view.message = await ctx.send(embed=embed, view=view)
    await view.wait()
    return view.choice


async def choose_platform(ctx):
    options = [
        discord.SelectOption(label="PC", value="pc", emoji=emojis.battlenet),
        discord.SelectOption(label="Playstation", value="psn", emoji=emojis.psn),
        discord.SelectOption(label="XBOX", value="xbl", emoji=emojis.xbl),
        discord.SelectOption(label="Nintendo Switch", value="nintendo-switch", emoji=emojis.switch),
    ]

    view = ChooseView(ctx=ctx)
    select = ChooseSelect(placeholder="Select a platform...")
    view.add_item(select)

    for option in options:
        select.append_option(option)

    view.message = await ctx.send("Select a platform...", view=view)
    await view.wait()
    return view.choice
