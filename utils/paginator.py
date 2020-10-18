"""This paginator has been written by EvieePy.

The MIT License (MIT) Copyright (c) 2018 EvieePy Permission is hereby
granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the
Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions: The above
copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED
"AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT
OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
import asyncio

import discord

from config import main_color


async def pager(entries, chunk: int):
    for x in range(0, len(entries), chunk):
        yield entries[x : x + chunk]


class Paginator:

    __slots__ = (
        "entries",
        "extras",
        "title",
        "description",
        "color",
        "footer",
        "length",
        "prepend",
        "append",
        "fmt",
        "timeout",
        "ordered",
        "controls",
        "controller",
        "pages",
        "current",
        "previous",
        "eof",
        "base",
        "names",
    )

    def __init__(self, **kwargs):
        self.entries = kwargs.get("entries", None)
        self.extras = kwargs.get("extras", None)

        self.title = kwargs.get("title", None)
        self.description = kwargs.get("description", None)
        self.color = kwargs.get("color", main_color)
        self.footer = kwargs.get("footer", None)

        self.length = kwargs.get("length", 10)
        self.prepend = kwargs.get("prepend", "")
        self.append = kwargs.get("append", "")
        self.fmt = kwargs.get("fmt", "")
        self.timeout = kwargs.get("timeout", 120)
        self.ordered = kwargs.get("ordered", False)

        self.controller = None
        self.pages = []
        self.names = []
        self.base = None

        self.current = 0
        self.previous = 0
        self.eof = 0

        self.controls = {"⏮": 0.0, "◀": -1, "⏹️": "stop", "▶": +1, "⏭": None}

    async def indexer(self, ctx, ctrl):
        if ctrl == "stop":
            ctx.bot.loop.create_task(self.stop_controller(self.base))

        elif isinstance(ctrl, int):
            self.current += ctrl
            if self.current > self.eof or self.current < 0:
                self.current -= ctrl
        else:
            self.current = int(ctrl)

    async def reaction_controller(self, ctx):
        bot = ctx.bot
        author = ctx.author

        self.base = await ctx.send(embed=self.pages[0])

        if len(self.pages) > 1:
            await self.base.edit(content="**Wait until i finish adding reactions...**")
            for reaction in self.controls:
                try:
                    await self.base.add_reaction(reaction)
                except discord.HTTPException:
                    return
            await self.base.edit(content=None)

        def check(r, u):
            if str(r) not in self.controls.keys():
                return False
            elif u.id == bot.user.id or r.message.id != self.base.id:
                return False
            elif u.id != author.id:
                return False
            return True

        while True:
            try:
                react, user = await bot.wait_for(
                    "reaction_add", check=check, timeout=self.timeout
                )
            except asyncio.TimeoutError:
                return ctx.bot.loop.create_task(self.stop_controller(self.base))

            control = self.controls.get(str(react))

            try:
                await self.base.remove_reaction(react, user)
            except discord.HTTPException:
                pass

            self.previous = self.current
            await self.indexer(ctx, control)

            if self.previous == self.current:
                continue

            try:
                await self.base.edit(embed=self.pages[self.current])
            except KeyError:
                pass

    async def stop_controller(self, message):
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        try:
            self.controller.cancel()
        except Exception:
            pass

    def formmater(self, chunk):
        return "\n".join(
            f"{self.prepend}{self.fmt}{value}{self.fmt[::-1]}{self.append}"
            for value in chunk
        )

    async def paginate(self, ctx):
        if isinstance(self.extras, discord.Embed):
            return await ctx.send(embed=self.extras)

        if self.extras:
            self.pages = [p for p in self.extras if isinstance(p, discord.Embed)]

        if self.entries:
            chunks = [c async for c in pager(self.entries, self.length)]

            for index, chunk in enumerate(chunks, start=1):
                page = discord.Embed(
                    title=f"{self.title} - {index}/{len(chunks)}", color=self.color
                )
                page.description = self.formmater(chunk)

                if hasattr(self, "footer"):
                    if self.footer:
                        page.set_footer(text=self.footer)
                self.pages.append(page)

        if not self.pages:
            raise ValueError(
                "There must be enough data to create at least 1 page for pagination."
            )

        self.eof = float(len(self.pages) - 1)
        self.controls["⏭"] = self.eof
        self.controller = ctx.bot.loop.create_task(self.reaction_controller(ctx))
