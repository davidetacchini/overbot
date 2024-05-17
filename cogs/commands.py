# Inspired by https://github.com/Rapptz/RoboDanny
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from asyncpg import PostgresConnectionError
from discord import InteractionType
from discord.ext import commands, tasks

if TYPE_CHECKING:
    from discord import Interaction

    from bot import OverBot


class Commands(commands.Cog):
    def __init__(self, bot: OverBot) -> None:
        self.bot = bot
        self._batch_lock = asyncio.Lock()
        self._data_batch: list[tuple[Any, ...]] = []

        self.bulk_insert_loop.add_exception_type(PostgresConnectionError)
        self.bulk_insert_loop.start()

    async def bulk_insert(self) -> None:
        query = """INSERT INTO command (name, guild_id, channel_id, author_id, created_at)
                   VALUES ($1, $2, $3, $4, $5);
                """

        if self._data_batch:
            for command in self._data_batch:
                await self.bot.pool.execute(query, *command)
            self._data_batch.clear()

    @tasks.loop(seconds=10.0)
    async def bulk_insert_loop(self) -> None:
        await self.bot.wait_until_ready()

        async with self._batch_lock:
            await self.bulk_insert()

    async def register_command(self, interaction: Interaction) -> None:
        if interaction.command is None:
            return

        command = interaction.command.qualified_name
        guild_id = interaction.guild_id or 0
        channel_id = interaction.channel_id or 0

        async with self._batch_lock:
            self._data_batch.append(
                (
                    command,
                    guild_id,
                    channel_id,
                    interaction.user.id,
                    interaction.created_at.utcnow(),
                )
            )

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction) -> None:
        if interaction.type is InteractionType.application_command:
            await self.register_command(interaction)

    def cog_unload(self) -> None:
        self.bulk_insert_loop.cancel()


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Commands(bot))
