import asyncio
from contextlib import suppress

import discord
from discord.ext import commands

from config import main_color


class Context(commands.Context):
    async def prompt(self, message, timeout=30, user=None, cancel="❌", confirm="✅"):
        user = user or self.author
        reactions = (cancel, confirm)

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

        async def cleanup():
            with suppress(discord.HTTPException):
                await msg.delete()

        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", check=check, timeout=timeout
            )
        except asyncio.TimeoutError:
            await cleanup()
            await self.send("You took too long to confirm.")

        await cleanup()

        return bool(reactions.index(str(reaction.emoji)))
