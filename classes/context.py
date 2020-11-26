import asyncio

import discord
from discord.ext import commands

from config import main_color


class Context(commands.Context):
    async def prompt(self, message, timeout=30, user=None):
        user = user or self.author
        reactions = ("❌", "✅")

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
            await self.bot.cleanup(msg)
            await self.send("You took too long to confirm.")

        await self.bot.cleanup(msg)

        return bool(reactions.index(str(reaction.emoji)))

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
