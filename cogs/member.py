import discord

from colour import Color
from discord.ext import commands

from utils.i18n import _, locale
from utils.checks import is_premium


def valid_color(argument):
    if argument.lower() == "none":
        return None

    try:
        color = Color(argument).get_hex_l()
    except (AttributeError, ValueError):
        raise commands.BadArgument(
            _(
                "You need to specify a hex (e.g. `#00ff00`) or a color code (e.g. `red`)."
            )
        ) from None
    return int(color.lstrip("#"), 16)


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

        member = "Active" if ctx.author.id in self.bot.premiums else "N/A"
        guild = "Active" if ctx.guild.id in self.bot.premiums else "N/A"

        description = _("Your Status: `{member}`\nServer Status: `{guild}`").format(
            member=member, guild=guild
        )

        to_check = (member, guild)
        if all(x == "N/A" for x in to_check):
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
            "You can use `{prefix}settings [setting] [value]` to update the value "
            "of a specific setting: `{prefix}settings color blue` will set the"
            "embeds color to blue."
        ).format(prefix=ctx.prefix)

        embed = discord.Embed(color=self.bot.color(ctx.author.id))
        author_name = _("{member}'s Settings").format(member=ctx.author.name)
        embed.set_author(name=author_name, icon_url=ctx.author.avatar_url)
        embed.description = description

        value = ""
        for subcommand in subcommands:
            if subcommand.short_doc:
                # remove `[Premium]` from docstring
                short_doc = subcommand.short_doc[12:]
            else:
                short_doc = _("No help found...")

            name = subcommand.name.capitalize()
            value += "**{name}** - `{setting}`\n*{description}*\n\n".format(
                name=name, description=short_doc, setting=settings[subcommand.name]
            )
            embed.add_field(name="Your settings", value=value)

        return embed

    @is_premium()
    @commands.group(invoke_without_command=True)
    @locale
    async def settings(self, ctx):
        _("""`[Premium]` Update your settings.""")
        embed = await self.embed_member_settings(ctx, ctx.command)
        await ctx.send(embed=embed)

    @is_premium()
    @settings.command()
    @locale
    async def color(self, ctx, *, color: valid_color):
        _(
            """`[Premium]` Set a custom color for the embeds.

        `<color>` - The color to use for the embeds. Enter `none` to reset.

        Formats:

        - Either 3 or 6 hex digit: #RGB or #RRGGBB
        - Color code: green, white, red etc...

        Note that few embeds won't change their color.
        """
        )
        if color is None:
            query = "UPDATE member SET embed_color = NULL WHERE id = $1;"
            await self.bot.pool.execute(query, ctx.author.id)
            try:
                del self.bot.embed_colors[ctx.author.id]
            except KeyError:
                return await ctx.send(_("Color already set to default."))
            else:
                return await ctx.send(_("Color successfully reset."))

        embed = discord.Embed(color=color)
        query = "UPDATE member SET embed_color = $1 WHERE id = $2;"
        await self.bot.pool.execute(query, color, ctx.author.id)
        self.bot.embed_colors[ctx.author.id] = color
        embed.description = _("Color successfully set.")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Member(bot))
