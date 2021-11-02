import discord

from discord.ext import commands


class Server(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def set_prefix(self, ctx, prefix):
        if ctx.prefix == prefix:
            return await ctx.send("The prefix you are trying to set is already in use.")
        elif len(prefix) > 5:
            return await ctx.send("Prefix may not be longer than 5 characters.")
        elif self.bot.prefixes.get(ctx.guild.id) and prefix == self.bot.prefix:
            del self.bot.prefixes[ctx.guild.id]
        else:
            self.bot.prefixes[ctx.guild.id] = prefix
        query = "UPDATE server SET prefix = $1 WHERE id = $2;"
        await self.bot.pool.execute(query, prefix, ctx.guild.id)
        await ctx.send(f"Prefix successfully set to `{prefix}`")

    async def get_top_guilds(self):
        query = """SELECT guild_id, COUNT(*) as commands
                   FROM command
                   WHERE (created_at >= date_trunc('week', CURRENT_TIMESTAMP - INTERVAL '1 week') and
                          created_at < date_trunc('week', CURRENT_TIMESTAMP))
                   GROUP BY guild_id
                   HAVING guild_id <> ALL($1::bigint[])
                   ORDER BY commands DESC
                   LIMIT 5;
                """
        return await self.bot.pool.fetch(query, self.bot.config.ignored_guilds)

    @commands.command()
    @commands.guild_only()
    async def prefix(self, ctx, prefix: commands.clean_content(escape_markdown=True) = None):
        """Shows / Updates this server prefix.

        `[prefix]` - The new server prefix to use.

        Surround the prefix with "" quotes if you want multiple
        words or trailing spaces. E.g. "ob ".

        `Manage Server` permission is required to change the prefix.
        """
        if prefix:
            if ctx.author.guild_permissions.manage_guild:
                await self.set_prefix(ctx, prefix)
            else:
                await ctx.send("`Manage Server` permission is required to change the prefix.")
        else:
            query = "SELECT prefix FROM server WHERE id = $1;"
            pre = await self.bot.pool.fetchval(query, ctx.guild.id)
            embed = discord.Embed(color=self.bot.color(ctx.author.id))
            embed.set_footer(text='Use "{ctx.clean_prefix}prefix [value]" to change it.')
            embed.add_field(name="Prefixes", value=f"1. {self.bot.user.mention}\n2. `{pre}`")
            await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 30.0, commands.BucketType.member)
    async def leaderboard(self, ctx):
        """Shows bot's weekly most active servers.

        It is based on commands runned.

        You can use this command once every 30 seconds.
        """
        async with ctx.typing():
            guilds = await self.get_weekly_most_active_guilds()
            embed = discord.Embed(color=self.bot.color(ctx.author.id))
            embed.title = "Most Active Servers"
            embed.url = self.bot.config.website + "/#servers"
            embed.set_footer(text="Tracking command usage since - 03/31/2021")

            board = []
            for index, guild in enumerate(guilds, start=1):
                g = self.bot.get_guild(guild["guild_id"])
                if not g:
                    continue
                board.append(
                    "{index}. **{str(g)}** ran a total of **{guild['commands']}** commands"
                )
            embed.description = "\n".join(board)
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Server(bot))
