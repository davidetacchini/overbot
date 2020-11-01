import discord
from discord.ext import commands


class Server(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def set_prefix(self, ctx, prefix):
        if len(prefix) > 5:
            return await ctx.send("Prefix may not be longer than 5 characters.")
        try:
            await self.bot.pool.execute(
                'UPDATE server SET "prefix"=$1 WHERE id=$2;', prefix, ctx.guild.id
            )
        except Exception as exc:
            await ctx.send(embed=self.bot.embed_exception(exc))
        else:
            await ctx.send(f"Prefix successfully set to `{prefix}`")

    @commands.command()
    @commands.guild_only()
    async def prefix(
        self, ctx, prefix: commands.clean_content(escape_markdown=True) = None
    ):
        """Displays information about the prefix or change it if a value is given."""
        if prefix:
            if ctx.author.guild_permissions.manage_guild:
                await self.set_prefix(ctx, prefix)
            else:
                await ctx.send(
                    "`Manage Server` permission is required to change the prefix."
                )
        else:
            pre = await self.bot.pool.fetchval(
                "SELECT prefix FROM server WHERE id=$1;", ctx.guild.id
            )
            embed = discord.Embed(color=discord.Color.blurple())
            embed.set_footer(text=f'Use "{ctx.prefix}prefix value" to change it.')
            embed.add_field(
                name="Prefixes", value=f"1. {self.bot.user.mention}\n2. `{pre}`"
            )
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Server(bot))
