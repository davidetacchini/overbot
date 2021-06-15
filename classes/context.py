import asyncio

import discord
from discord.ext import commands

from utils.i18n import _
from utils.paginator import NoChoice


class Context(commands.Context):
    async def prompt(self, message, timeout=30.0, user=None):
        user = user or self.author
        reactions = ("✅", "❌")

        if user.id == self.bot.user.id:
            return False

        embed = discord.Embed(color=self.bot.color(user.id))
        embed.title = _("Confirmation")
        embed.description = message
        msg = await self.send(embed=embed)

        for emoji in reactions:
            await msg.add_reaction(emoji)

        def check(r, u):
            if u.id != user.id:
                return False
            if r.message.id != msg.id:
                return False
            if str(emoji) not in reactions:
                return False
            return True

        try:
            reaction, unused = await self.bot.wait_for(
                "reaction_add", check=check, timeout=timeout
            )
        except asyncio.TimeoutError:
            raise NoChoice() from None
        else:
            return not bool(reactions.index(str(reaction.emoji)))
        finally:
            await self.bot.cleanup(msg)

    def tick(self, opt, label=None):
        lookup = {
            True: "<:online:648186001361076243>",
            False: "<:dnd:648185968209428490>",
            None: "<:offline:648185992360099865>",
        }
        emoji = lookup.get(opt, "<:dnd:648185968209428490>")
        if label is not None:
            return f"{emoji}: {label}"
        return emoji
