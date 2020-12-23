import asyncio

import discord
from discord.ext import commands

from config import main_color
from utils.paginator import NoChoice


class Context(commands.Context):
    async def prompt(self, message, timeout=30.0, user=None):
        user = user or self.author
        reactions = ("✅", "❌")

        if user.id == self.bot.user.id:
            return False

        embed = discord.Embed(color=main_color)
        embed.title = "Confirmation"
        embed.description = message
        msg = await self.send(embed=embed)

        for emoji in reactions:
            await msg.add_reaction(emoji)

        def check(r, u):
            return u == user and str(r.emoji) in reactions and r.message.id == msg.id

        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", check=check, timeout=timeout
            )
        except asyncio.TimeoutError:
            raise NoChoice("You took to long to confirm.")
        else:
            # return not bool since we want the checkmark to be the first
            # reaction. Since it's the first reaction, its index is 0 which
            # is equivalent to False, but we want it to return True.
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
