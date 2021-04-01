import discord
from colour import Color
from discord.ext import commands

from utils.i18n import _, locale
from utils.checks import is_premium


class Member(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @locale
    async def premium(self, ctx):
        _("""Shows your current premium status.""")
        embed = discord.Embed(color=self.bot.color(ctx.author.id))
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

    async def get_member_settings(self, member_id):
        color = self.bot.color(member_id)
        color_value = str(hex(color)).replace("0x", "#")

        return {
            "color": color_value,
        }

    async def embed_member_settings(self, ctx, command):
        subcommands = getattr(command, "commands", None)
        settings = await self.get_member_settings(ctx.author.id)

        description = _(
            "Use `{prefix}settings [setting] [value]` to update a value "
            "of a specific setting. E.g.: `{prefix}settings color blue` "
            "will set the embeds color to blue.\n\n**Your settings**"
        ).format(prefix=ctx.prefix)

        embed = discord.Embed(color=self.bot.color(ctx.author.id))
        author_name = _("{member}'s Settings").format(member=ctx.author.name)
        embed.set_author(name=author_name, icon_url=ctx.author.avatar_url)
        embed.description = description

        for subcommand in subcommands:
            if subcommand.short_doc:
                # remove `[Premium]` from docstring
                short_doc = subcommand.short_doc[12:]
            else:
                short_doc = _("No help found...")

            name = subcommand.name.capitalize()
            value = "*{description}*\nCurrent: `{setting}`".format(
                description=short_doc, setting=settings[subcommand.name]
            )
            embed.add_field(name=name, value=value, inline=False)

        return embed

    @is_premium()
    @commands.group(invoke_without_command=True)
    @locale
    async def settings(self, ctx, command: str = None):
        _("""`[Premium]` Update your settings.""")
        embed = await self.embed_member_settings(ctx, ctx.command)
        await ctx.send(embed=embed)

    @is_premium()
    @settings.command()
    @locale
    async def color(self, ctx, *, color: str):
        _(
            """`[Premium]` Set a custom color for the embeds.

        `<color>` - The color to use for the embeds.

        Formats:
        - Either 3 or 6 hex digit: #RGB or #RRGGBB
        - Color code: green, white, red etc...

        Enter `none` or `default` to reset the color.
        Notice that few embeds will not change their color.
        """
        )

        if color in ("none", "default"):
            query = "UPDATE member SET embed_color = NULL WHERE id = $1;"
            await self.bot.pool.execute(query, ctx.author.id)
            del self.bot.embed_colors[ctx.author.id]
            return await ctx.send(_("Color successfully reset."))

        try:
            clr = Color(color).get_hex_l()
        except (AttributeError, ValueError):
            message = _(
                "You need to specify a hex (Example: `#00ff00`) or a color code (Example: `red`)."
            )
            return await ctx.send(message)

        clr = int(clr.lstrip("#"), 16)
        embed = discord.Embed(color=clr)

        try:
            query = "UPDATE member SET embed_color = $1 WHERE id = $2;"
            await self.bot.pool.execute(query, clr, ctx.author.id)
            self.bot.embed_colors[ctx.author.id] = clr
        except Exception as e:
            await ctx.send(embed=self.bot.embed_exception(e))
        else:
            embed.description = _("Color successfully set to `{color}`").format(
                color=color
            )
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Member(bot))
