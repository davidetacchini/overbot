import discord
from discord.ext import commands


class Server(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def set_prefix(self, ctx, prefix):
        if len(prefix) > 5:
            return await ctx.send("Prefix may not be longer than 5 characters.")
        if prefix == self.bot.prefix:
            del self.bot.prefixes[ctx.guild.id]
        else:
            self.bot.prefixes[ctx.guild.id] = prefix
        await self.bot.pool.execute(
            'UPDATE server SET "prefix"=$1 WHERE id=$2;', prefix, ctx.guild.id
        )
        await ctx.send(f"Prefix successfully set to `{prefix}`")

    @commands.command()
    @commands.guild_only()
    async def prefix(
        self, ctx, prefix: commands.clean_content(escape_markdown=True) = None
    ):
        """Either see the prefix or change it.

        `[prefix]` - The new server prefix to use.

        You must have Manage Server permission to use this command.
        """
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
            embed.set_footer(
                text=f'Use "{self.bot.clean_prefix(ctx)}prefix value" to change it.'
            )
            embed.add_field(
                name="Prefixes", value=f"1. {self.bot.user.mention}\n2. `{pre}`"
            )
            await ctx.send(embed=embed)

    @staticmethod
    def get_placement(place):
        placements = {
            1: "<:top500:632281138832080926>",
            2: "<:grandmaster:632281128966946826>",
            3: "<:master:632281117394993163>",
            4: "<:diamond:632281105571119105>",
            5: "<:platinum:632281092875091998>",
        }
        return placements.get(place)

    @commands.command()
    @commands.cooldown(1, 30.0, commands.BucketType.member)
    async def leaderboard(self, ctx):
        """Displays a leaderboard of the 5 most active servers.

        It is based on commands runned.
        """
        async with ctx.typing():
            guilds = await self.bot.pool.fetch(
                "SELECT id, commands_runned FROM server WHERE id NOT IN "
                "(638339745117896745, 550685823784321035) ORDER BY commands_runned DESC LIMIT 5;"
            )
            embed = discord.Embed()
            embed.title = "Five Most Active Servers"
            embed.url = self.bot.config.website
            embed.set_footer(text="Tracking command usage since • 11/26/2020")

            board = ""
            for i, guild in enumerate(guilds, start=1):
                g = self.bot.get_guild(guild["id"])
                board += (
                    f"{self.get_placement(i)} **{str(g)}**"
                    f" runned a total of **{guild['commands_runned']}** commands\n"
                    f"Joined on: **{str(g.me.joined_at).split(' ')[0]}**\n"
                )
                if i < 5:
                    board += "-----------\n"
            embed.description = board
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Server(bot))
