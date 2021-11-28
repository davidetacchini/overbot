from contextlib import suppress

import discord

from utils import emojis

from .player import Player
from .context import Context

MAX_NICKNAME_LENGTH = 32
ROLES = {
    "tank": emojis.u_tank,
    "damage": emojis.u_damage,
    "support": emojis.u_support,
}


class Nickname:
    __slots__ = ("ctx", "profile", "member")

    def __init__(self, ctx: "Context", *, profile: Player = None) -> None:
        self.ctx = ctx
        self.profile = profile
        self.member: discord.Member = ctx.author

    async def exists(self) -> bool:
        query = "SELECT id FROM nickname WHERE id = $1;"
        ret = await self.ctx.bot.pool.fetchval(query, self.member.id)
        return True if ret else False

    async def _make(self) -> str:
        ratings = self.profile.resolve_ratings()
        if not ratings:
            return f"{self.member.name[:21]} [Unranked]"

        tmp = ""
        for key, value in ratings.items():
            tmp += f"{ROLES.get(key)}{value}/"

        # tmp[:-1] removes the last slash
        tmp = "[" + tmp[:-1] + "]"

        # dinamically assign the nickname's length based on
        # player's SR. -1 indicates the space between
        # the member's name and the SR
        x = MAX_NICKNAME_LENGTH - len(tmp) - 1
        name = self.member.name[:x]
        return name + " " + tmp

    async def update(self) -> None:
        if not await self.exists():
            return

        nick = await self._make()
        with suppress(Exception):
            await self.member.edit(nick=nick)

    async def set_or_remove(self, *, profile_id: int = None, remove: bool = False) -> None:
        if not remove:
            nick = await self._make()
        else:
            nick = None

        try:
            await self.member.edit(nick=nick)
        except discord.Forbidden:
            await self.ctx.send(
                "I can't change nicknames in this server. Grant me `Manage Nicknames` permission."
            )
        except discord.HTTPException:
            await self.ctx.send("Something bad happened while updating your nickname.")

        if not remove:
            query = "INSERT INTO nickname(id, server_id, profile_id) VALUES($1, $2, $3);"
            await self.ctx.bot.pool.execute(query, self.member.id, self.ctx.guild.id, profile_id)
            await self.ctx.send("Nickname successfully set.")
        else:
            query = "DELETE FROM nickname WHERE id = $1;"
            await self.ctx.bot.pool.execute(query, self.member.id)
            await self.ctx.send("Nickname successfully removed.")
