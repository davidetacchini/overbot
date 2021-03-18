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
        embed = discord.Embed(color=self.bot.color)
        embed.title = _("Premium status")
        embed.description = _(
            "Current status: `N/A`\n[Upgrade to Premium]({premium})".format(
                premium=self.bot.config.premium
            )
        )

        guild = self.bot.get_guild(self.bot.config.support_server_id)

        try:
            member = await guild.fetch_member(ctx.author.id)
        except discord.HTTPException:
            return await ctx.send(embed=embed)

        role = discord.utils.get(member.roles, name="Premium") is not None

        if role:
            embed.description = _("Current status: `Active`")

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

        Notice that few embeds will not change their color.

        Formats:
        - Either 3 or 6 hex digit: #RGB or #RRGGBB.
        - Color code: red, white, black etc...

        You can find a list of all the color codes at: https://htmlcolorcodes.com/color-names/
        """
        )
        # white color doesn't work for embeds
        try:
            if not Color(color) == Color("white"):
                c = Color(color).get_hex_l()
            else:
                c = Color("#fffff0").get_hex_l()
        except (AttributeError, ValueError):
            return await ctx.send(
                _(
                    "Wrong format! Supported formats:\n"
                    "1. Either 3 or 6 hex digit. Example: `#fff` or `#ffffff`.\n"
                    "2. Color code. Example: `red`, `white`, `limegreen` and so on...\n"
                    "You can find a list of all available colors at the following link: https://htmlcolorcodes.com/color-names/"
                )
            )

        c = int(c.replace("#", "0x"), 16)
        embed = discord.Embed(color=discord.Color(c))
        embed.description = _("Color successfully set to `{color}`").format(color=color)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Member(bot))
