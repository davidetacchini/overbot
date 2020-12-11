import asyncio
from typing import Union, Optional
from contextlib import suppress

import discord
from discord.ext.commands import CommandInvokeError

from config import main_color


class NoChoice(CommandInvokeError):
    """Exception raised when no choice is given."""

    pass


class BasePaginator:
    __slots__ = (
        "entries",
        "timeout",
        "title",
        "footer",
        "image",
        "color",
        "reactions",
        "embed",
        "description",
        "ctx",
        "bot",
        "author",
        "message",
    )

    def __init__(
        self,
        entries: Optional[Union[list, tuple]] = None,
        *,
        timeout: float = 30.0,
        title: Optional[str] = None,
        image: Optional[str] = None,
        footer: Optional[str] = None,
    ):
        self.entries = entries
        self.timeout = timeout
        self.title = title
        self.image = image
        self.footer = footer

        self.color = main_color
        self.reactions = None
        self.embed = None
        self.description = []
        self.ctx = None
        self.bot = None
        self.author = None
        self.message = None

    def init_embed(self):
        embed = discord.Embed(color=main_color)
        embed.set_author(name=str(self.author), icon_url=self.author.avatar_url)

        if self.title:
            embed.title = self.title

        if self.image:
            embed.set_image(url=self.image)

        if self.footer:
            embed.set_footer(text=self.footer)

        return embed

    async def add_reactions(self):
        for reaction in self.reactions:
            try:
                await self.message.add_reaction(reaction)
            except (discord.HTTPException, discord.Forbidden):
                return

    async def cleanup(self):
        with suppress(discord.HTTPException, discord.Forbidden):
            await self.message.delete()

    async def paginator(self):
        raise NotImplementedError

    async def start(self, ctx):
        raise NotImplementedError


class Link(BasePaginator):

    __slots__ = ("title", "footer")

    def __init__(self, *, title, footer):
        super().__init__(title=title, footer=footer)
        self.reactions = {
            "<:battlenet:679469162724196387>": "pc",
            "<:psn:679468542541693128>": "psn",
            "<:xbl:679469487623503930>": "xbl",
            "<:nsw:752653766377078817>": "nintendo-switch",
            "❌": "close",
        }

    async def paginator(self):
        self.message = await self.ctx.send(embed=self.embed)
        self.bot.loop.create_task(self.add_reactions())

        def check(r, u):
            if u.id != self.author.id:
                return False
            if u.id == self.bot.user.id:
                return False
            if r.message.id != self.message.id:
                return False
            if str(r.emoji) not in self.reactions:
                return False
            return True

        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", check=check, timeout=self.timeout
            )
        except asyncio.TimeoutError:
            raise NoChoice("You took too long to reply.")
        else:
            return self.reactions.get(str(reaction.emoji))
        finally:
            await self.cleanup()

    async def start(self, ctx):
        self.ctx = ctx
        self.bot = ctx.bot
        self.author = ctx.author

        self.embed = self.init_embed()
        for key, value in self.reactions.items():
            self.description.append(f"{key} - {value.replace('-', ' ').upper()}")
        self.embed.description = "\n".join(self.description)

        return await self.paginator()


class Choose(BasePaginator):

    __slots__ = ("entries", "timeout", "title", "image", "footer")

    def __init__(self, entries, timeout, title, image, footer):
        super().__init__(
            entries, timeout=timeout, title=title, image=image, footer=footer
        )
        self.reactions = []

    async def paginator(self):
        self.message = await self.ctx.send(embed=self.embed)
        self.bot.loop.create_task(self.add_reactions())

        def check(r, u):
            if u.id != self.author.id:
                return False
            if u.id == self.bot.user.id:
                return False
            if r.message.id != self.message.id:
                return False
            if str(r.emoji) not in self.reactions:
                return False
            return True

        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", check=check, timeout=self.timeout
            )
        except asyncio.TimeoutError:
            raise NoChoice("You took too long to reply.")
        else:
            return self.entries[self.reactions.index(str(reaction))]
        finally:
            await self.cleanup()

    async def start(self, ctx):
        self.ctx = ctx
        self.bot = ctx.bot
        self.author = ctx.author

        for index, entry in enumerate(self.entries, start=1):
            self.reactions.append(f"{index}\u20e3")
            self.description.append(f"{index}. {entry}")

        self.embed = self.init_embed()
        self.embed.description = "\n".join(self.description)

        return await self.paginator()
