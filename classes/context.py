import re

import discord

from discord.ext import commands

from utils import emojis


class PromptView(discord.ui.View):
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
        await self.message.delete()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, button, interaction):
        self.value = True
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, button, interaction):
        self.value = False
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def prompt(self, payload):
        if isinstance(payload, str):
            kwargs = {"content": payload, "embed": None}
        elif isinstance(payload, discord.Embed):
            kwargs = {"content": None, "embed": payload}
        view = PromptView(author_id=self.author.id)
        view.message = await self.send(**kwargs, view=view)
        await view.wait()
        return view.value

    @property
    def clean_prefix(self):
        user = self.guild.me if self.guild else self.bot.user
        pattern = re.compile(r"<@!?%s>" % user.id)
        return pattern.sub("@%s" % user.display_name.replace("\\", r"\\"), self.prefix)

    def tick(self, opt, label=None):
        lookup = {
            True: emojis.online,
            False: emojis.dnd,
            None: emojis.offline,
        }
        emoji = lookup.get(opt, emojis.dnd)
        if label is not None:
            return f"{emoji}: {label}"
        return emoji
