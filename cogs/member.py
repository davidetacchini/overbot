import discord
from colour import Color
from discord.ext import commands

from utils.i18n import _, locale
from utils.checks import is_premium


class Member(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @locale
    async def premium(self, ctx):
        _("""Shows your current premium status.""")
        embed = discord.Embed(color=self.bot.get_color(ctx.author.id))
        embed.title = _("Premium Status")

        one_premium = False

        if ctx.author.id in self.bot.premiums:
            member = "Active"
            one_premium = True
        else:
            member = "N/A"

        if ctx.guild.id in self.bot.premiums:
            guild = "Active"
            one_premium = True
        else:
            guild = "N/A"

        description = _("Your Status: `{member}`\nServer Status: `{guild}`").format(
            member=member, guild=guild
        )

        if one_premium is False:
            link = _("[Upgrade to Premium]({premium})").format(
                premium=self.bot.config.premium
            )
            description = description + "\n" + link

        embed.description = description
        await ctx.send(embed=embed)

    @is_premium()
    @commands.group(invoke_without_command=True)
    @locale
    async def settings(self, ctx, command: str = None):
        _("""`[Premium]` Update your settings.""")
        embed = self.bot.get_subcommands(ctx, ctx.command)
        await ctx.send(embed=embed)

    @is_premium()
    @settings.command()
    @locale
    async def color(self, ctx, *, color: str):
        _(
            """`[Premium]` Set a custom color for the embeds.

        `<color>` - The color to use for the embeds.

        Formats:
        - Either 3 or 6 hex digit: #RGB or #RRGGBB.
        - Color code: green, white, red etc...

        Enter `none` or `default` to reset the color.
        Notice that few embeds will not change their color.
        """
        )
        # TODO: enter `none` or `default` to reset color
        try:
            if not Color(color) == Color("white"):
                c = Color(color).get_hex_l()
            else:
                # pure white doesn't work for embeds
                c = Color("#fffff0").get_hex_l()
        except (AttributeError, ValueError):
            embed = discord.Embed(color=discord.Color.red())
            embed.description = _(
                "Invalid color! Supported color formats:\n"
                "1. Either 3 or 6 hex digit: `#RGB` or `#RRGGBB` \n"
                "2. Color code. Example: `green`, `white`, `red`, etc...\n"
                "[Click here](https://htmlcolorcodes.com/color-names/) to have a look at the available color codes."
            )
            return await ctx.send(embed=embed)

        # since discord.Color() takes only a raw integer value,
        # the color must be converted to a base 16 integer and
        # then passed to discord.Color()
        c = int(c.lstrip("#"), 16)
        embed = discord.Embed(color=discord.Color(c))

        try:
            query = "UPDATE member SET embed_color = $1 WHERE id = $1;"
            await self.bot.pool.execute(query, c, ctx.author.id)
            self.bot.embed_colors[ctx.author.id] = c
        except Exception as e:
            await ctx.send(embed=self.bot.embed_exception(e))
        else:
            embed.description = _("Color successfully set to `{color}`").format(
                color=color
            )
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Member(bot))
