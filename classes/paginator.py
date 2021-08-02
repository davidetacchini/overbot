import asyncio

from typing import Union, Optional

import discord

from pygicord import CannotAddReactions, CannotUseExternalEmojis

from utils.i18n import _

from .exceptions import NoChoice

PLATFORMS = {
    "pc": "PC",
    "psn": "Playstation",
    "xbl": "Xbox",
    "nintendo-switch": "Switch",
}


class BasePaginator:

    __slots__ = (
        "entries",
        "timeout",
        "title",
        "footer",
        "image",
        "emojis",
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
        timeout: float = 60.0,
        title: Optional[str] = None,
        image: Optional[str] = None,
        footer: Optional[str] = None,
    ):
        self.entries = entries
        self.timeout = timeout
        self.title = title
        self.image = image
        self.footer = footer

        self.emojis = None
        self.embed = None
        self.description = []
        self.ctx = None
        self.bot = None
        self.author = None
        self.message = None

    def init_embed(self):
        embed = discord.Embed(color=self.bot.color(self.author.id))
        embed.set_author(name=str(self.author), icon_url=self.author.avatar_url)

        if self.title:
            if len(self.title) <= 256:
                embed.title = self.title
            else:
                self.description.append(self.title)

        if self.image:
            embed.set_image(url=self.image)

        if self.footer:
            embed.set_footer(text=self.footer)

        return embed

    def result(self, payload):
        raise NotImplementedError

    async def add_reactions(self):
        for emoji in self.emojis:
            try:
                await self.message.add_reaction(emoji)
            except (discord.NotFound, discord.HTTPException):
                pass

    async def session(self):
        self.message = await self.ctx.send(embed=self.embed)
        self.bot.loop.create_task(self.add_reactions())

        def check(r, u):
            return (
                u.id == self.author.id
                and u.id != self.bot.user.id
                and r.message.id == self.message.id
                and str(r.emoji) in self.emojis
            )

        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", check=check, timeout=self.timeout
            )
        except asyncio.TimeoutError:
            raise NoChoice() from None
        else:
            return self.result(reaction)
        finally:
            try:
                await self.message.delete()
            except discord.HTTPException:
                pass

    def _check_permissions(self, ctx):
        permissions = ctx.channel.permissions_for(ctx.me)

        if not permissions.send_messages:
            return

        if not permissions.add_reactions:
            raise CannotAddReactions()

        if not permissions.use_external_emojis:
            raise CannotUseExternalEmojis()

    async def start(self, ctx):
        self._check_permissions(ctx)
        return await self.session()


class Link(BasePaginator):
    def __init__(self):
        title = _("Platform")
        footer = _("React with the platform you play on...")
        super().__init__(title=title, footer=footer)
        self.emojis = {
            "<:battlenet:679469162724196387>": "pc",
            "<:psn:679468542541693128>": "psn",
            "<:xbl:679469487623503930>": "xbl",
            "<:nsw:752653766377078817>": "nintendo-switch",
            "❌": None,
        }

    def result(self, reaction):
        return self.emojis.get(str(reaction.emoji))

    def update_embed(self):
        self.embed = self.init_embed()

        for key, value in self.emojis.items():
            if value is None:
                continue
            value = PLATFORMS.get(value)
            self.description.append(f"{key} - {value}")
        self.embed.description = "\n".join(self.description)

    async def start(self, ctx):
        self.ctx = ctx
        self.bot = ctx.bot
        self.author = ctx.author
        self.update_embed()
        return await super().start(ctx)


class Update(Link):

    __slots__ = ("platform", "username")

    def __init__(self, platform, username):
        super().__init__()
        self.platform = platform
        self.username = username

    async def start(self, ctx):
        self.ctx = ctx
        self.bot = ctx.bot
        self.author = ctx.author
        self.update_embed()

        self.description.append(_("\nProfile to update:"))
        self.embed.description = "\n".join(self.description)

        self.embed.add_field(name=_("Platform"), value=self.platform)
        self.embed.add_field(name=_("Username"), value=self.username)
        return await super(Link, self).start(ctx)


class Choose(BasePaginator):
    def __init__(self, entries, *, timeout, title, image, footer):
        super().__init__(
            entries, timeout=timeout, title=title, image=image, footer=footer
        )
        self.emojis = []

    def result(self, reaction):
        return self.entries[self.emojis.index(str(reaction))]

    async def start(self, ctx):
        self.ctx = ctx
        self.bot = ctx.bot
        self.author = ctx.author
        self.embed = self.init_embed()

        for index, entry in enumerate(self.entries, start=1):
            self.emojis.append(f"{index}\u20e3")
            self.description.append(f"{index}. {entry}")

        self.embed.description = "\n".join(self.description)
        return await super().start(ctx)
