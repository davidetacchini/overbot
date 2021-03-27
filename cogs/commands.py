# inspired by https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/stats.py#L64

import asyncio

from asyncpg import PostgresConnectionError
from discord.ext import tasks, commands


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._batch_lock = asyncio.Lock(loop=bot.loop)
        self._data_batch = []

        self.bulk_insert_loop.add_exception_type(PostgresConnectionError)
        self.bulk_insert_loop.start()

    async def bulk_insert(self):
        query = """INSERT INTO command (name, guild_id, channel_id, author_id, created_at, prefix, failed)
                   VALUES ($1, $2, $3, $4, $5, $6, $7);
                """

        if self._data_batch:
            await self.bot.pool.executemany(query, self._data_batch)
            self._data_batch.clear()

    @tasks.loop(seconds=10.0)
    async def bulk_insert_loop(self):
        await self.bot.wait_until_ready()

        async with self._batch_lock:
            await self.bulk_insert()

    async def register_command(self, ctx):
        if ctx.command is None:
            return

        command = ctx.command.qualified_name
        if ctx.guild is not None:
            guild_id = ctx.guild.id
        else:
            guild_id = 0  # direct messages

        async with self._batch_lock:
            self._data_batch.append(
                (
                    command,
                    guild_id,
                    ctx.channel.id,
                    ctx.author.id,
                    ctx.message.created_at,
                    ctx.prefix,
                    ctx.command_failed,
                )
            )

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        await self.register_command(ctx)

    def cog_unload(self):
        self.bulk_insert_loop.cancel()


def setup(bot):
    bot.add_cog(Commands(bot))
