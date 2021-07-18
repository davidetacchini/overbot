import re
import asyncio

import discord

from pygicord import CannotAddReactions
from discord.ext import commands

from utils.i18n import _
from classes.exceptions import NoChoice


class Context(commands.Context):
    CHECK = "\N{WHITE HEAVY CHECK MARK}"
    XMARK = "\N{CROSS MARK}"

    @property
    def clean_prefix(self):
        user = self.guild.me if self.guild else self.bot.user
        pattern = re.compile(r"<@!?%s>" % user.id)
        return pattern.sub("@%s" % user.display_name.replace("\\", r"\\"), self.prefix)

    async def prompt(self, text):
        if not self.channel.permissions_for(self.me).add_reactions:
            raise CannotAddReactions()

        user = self.author
        reactions = (self.CHECK, self.XMARK)

        if user.id == self.bot.user.id:
            return False

        embed = discord.Embed(color=self.bot.color(user.id))
        embed.title = _("Are you sure?")
        embed.description = text
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
                "reaction_add", check=check, timeout=30.0
            )
        except asyncio.TimeoutError:
            raise NoChoice() from None
        else:
            return not bool(reactions.index(str(reaction.emoji)))
        finally:
            try:
                await msg.delete()
            except discord.HTTPException:
                pass

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
