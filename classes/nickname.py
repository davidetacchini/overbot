from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from utils import emojis

if TYPE_CHECKING:
    from bot import OverBot

    from .profile import Profile

MAX_NICKNAME_LENGTH = 32


class Nickname:
    __slots__ = ("interaction", "bot", "profile", "member", "guild")

    def __init__(self, interaction: discord.Interaction, *, profile: None | Profile = None) -> None:
        self.interaction = interaction
        self.bot: OverBot = interaction.client
        self.profile = profile
        self.member: discord.Member = interaction.user
        self.guild: None | discord.Guild = interaction.guild

    async def exists(self) -> bool:
        query = "SELECT EXISTS (SELECT TRUE FROM nickname WHERE id = $1);"
        return bool(await self.bot.pool.fetchval(query, self.member.id))

    async def _generate(self) -> str:
        ratings = self.profile.resolve_ratings(formatted=False)
        if not ratings:
            return f"{self.member.name[:21]} [Unranked]"

        role_to_emoji = {
            "tank": emojis.u_tank,
            "damage": emojis.u_damage,
            "support": emojis.u_support,
        }
        ratings_abbrv = {
            "bronze": "BR",
            "silver": "SI",
            "gold": "GO",
            "platinum": "PL",
            "diamond": "DI",
            "master": "MA",
            "grandmaster": "GM",
        }

        tmp = ""
        for key, value in ratings.items():
            icon = role_to_emoji.get(key)
            group = ratings_abbrv.get(value["group"].lower())
            tier = value["tier"]
            tmp += f"{icon}{group}-{tier}/"

        # tmp[:-1] removes the last slash
        tmp = "[" + tmp[:-1] + "]"

        # dinamically assign the nickname's length based on player's SR.
        # -1 indicates the space between the user's name and the SR.
        x = MAX_NICKNAME_LENGTH - len(tmp) - 1
        name = self.member.name[:x]
        return name + " " + tmp

    async def update(self) -> None:
        if not await self.exists():
            return

        nick = await self._generate()
        try:
            await self.member.edit(nick=nick)
        except Exception:
            pass

    async def set_or_remove(self, *, profile_id: None | int = None, remove: bool = False) -> None:
        if not remove:
            nick = await self._generate()
        else:
            nick = None

        try:
            await self.member.edit(nick=nick)
        except discord.HTTPException:
            await self.interaction.followup.send(
                "Something bad happened while updating your nickname.", ephemeral=True
            )

        if not remove:
            query = "INSERT INTO nickname (id, server_id, profile_id) VALUES ($1, $2, $3);"
            await self.bot.pool.execute(query, self.member.id, self.guild.id, profile_id)
            await self.interaction.followup.send("Nickname successfully set.", ephemeral=True)
        else:
            query = "DELETE FROM nickname WHERE id = $1;"
            await self.bot.pool.execute(query, self.member.id)
            await self.interaction.followup.send("Nickname successfully removed.", ephemeral=True)
