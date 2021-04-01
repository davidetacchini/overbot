import discord
from discord.ext import commands

from utils.i18n import _, locale


class Server(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def set_prefix(self, ctx, prefix):
        if ctx.prefix == prefix:
            return await ctx.send(
                _("The prefix you are trying to set is already in use.")
            )
        elif len(prefix) > 5:
            return await ctx.send(_("Prefix may not be longer than 5 characters."))
        elif prefix == self.bot.prefix:
            del self.bot.prefixes[ctx.guild.id]
        else:
            self.bot.prefixes[ctx.guild.id] = prefix
        query = "UPDATE server SET prefix = $1 WHERE id = $2;"
        await self.bot.pool.execute(query, prefix, ctx.guild.id)
        await ctx.send(_("Prefix successfully set to `{prefix}`").format(prefix=prefix))

    @commands.command()
    @commands.guild_only()
    @locale
    async def prefix(
        self, ctx, prefix: commands.clean_content(escape_markdown=True) = None
    ):
        _(
            """Either see the prefix or change it.

        `[prefix]` - The new server prefix to use.

        You must have Manage Server permission to use this command.
        """
        )
        if prefix:
            if ctx.author.guild_permissions.manage_guild:
                await self.set_prefix(ctx, prefix)
            else:
                await ctx.send(
                    _("`Manage Server` permission is required to change the prefix.")
                )
        else:
            query = "SELECT prefix FROM server WHERE id = $1;"
            pre = await self.bot.pool.fetchval(query, ctx.guild.id)
            embed = discord.Embed(color=self.bot.color(ctx.author.id))
            embed.set_footer(
                text=_('Use "{prefix}prefix value" to change it.').format(
                    prefix=self.bot.clean_prefix(ctx)
                )
            )
            embed.add_field(
                name=_("Prefixes"), value=f"1. {self.bot.user.mention}\n2. `{pre}`"
            )
            await ctx.send(embed=embed)

    @staticmethod
    def get_placement(place):
        placements = {
            1: ":first_place:",
            2: ":second_place:",
            3: ":third_place:",
            4: ":four:",
            5: ":five:",
        }
        return placements.get(place)

    @commands.command()
    @commands.cooldown(1, 30.0, commands.BucketType.member)
    @locale
    async def leaderboard(self, ctx):
        _(
            """Shows OverBot's most active servers.

        It is based on commands runned.
        """
        )
        async with ctx.typing():
            query = """SELECT guild_id, COUNT(*) as commands
                       FROM command
                       GROUP BY guild_id
                       HAVING guild_id <> ALL($1::bigint[])
                       ORDER BY commands DESC
                       LIMIT 5;
                    """
            guilds = await self.bot.pool.fetch(query, self.bot.config.ignored_guilds)
            embed = discord.Embed(color=self.bot.color(ctx.author.id))
            embed.title = _("Most Active Servers")
            embed.url = self.bot.config.website + "/#servers"
            embed.set_footer(text=_("Tracking command usage since - 03/31/2021"))

            board = []
            for index, guild in enumerate(guilds, start=1):
                cur_guild = self.bot.get_guild(guild["guild_id"])
                placement = self.get_placement(index)
                joined_on = str(cur_guild.me.joined_at).split(" ")[0]

                board.append(
                    _(
                        "{placement} **{guild}**"
                        " ran a total of **{commands}** commands\n"
                        "Joined on: **{joined_on}**"
                    ).format(
                        placement=placement,
                        guild=str(cur_guild),
                        commands=guild["commands"],
                        joined_on=joined_on,
                    )
                )

                if index < 5:
                    board.append("-----------")

            embed.description = "\n".join(board)
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Server(bot))
