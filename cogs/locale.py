import discord
from discord.ext import commands

from utils import i18n
from utils.i18n import _, locale


def valid_locale(argument):
    valid = {
        "it_it": "it_IT",
        "it": "it_IT",
        "en_us": "en_US",
        "en": "en_US",
        "de_de": "de_DE",
        "de": "de_DE",
        "ru_ru": "ru_RU",
        "ru": "ru_RU",
        "ko_kr": "ko_KR",
        "ko": "ko_KR",
        "ja_jp": "ja_JP",
        "ja": "ja_JP",
        "fr_fr": "fr_FR",
        "fr": "fr_FR",
    }

    try:
        locale = valid[argument.lower()]
    except KeyError:
        raise commands.BadArgument(
            _("Unknown locale: **{locale}**").format(locale=argument)
        ) from None
    return locale


class Locale(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.locales = {}

    async def set_locale(self, member_id, locale):
        query = """INSERT INTO member(id, locale)
                   VALUES($1, $2)
                   ON CONFLICT (id) DO
                   UPDATE SET locale = $2;
                """
        await self.bot.pool.execute(query, member_id, locale)
        self.bot.locales[member_id] = locale

    async def get_locale(self, member_id):
        query = "SELECT locale FROM member WHERE id = $1;"
        return await self.bot.pool.fetchval(query, member_id)

    async def update_locale(self, member_id):
        locale = self.bot.locales.get(member_id)
        if not locale:
            locale = await self.get_locale(member_id)
            self.bot.locales[member_id] = locale
        return locale

    @commands.group(invoke_without_command=True, aliases=["locale", "lang"])
    @locale
    async def language(self, ctx):
        _("""Displays your current language set and all the available languages.""")
        embed = discord.Embed(color=self.bot.color(ctx.author.id))
        embed.title = _("Available Languages")
        current_locale = self.bot.locales[ctx.author.id] or i18n.current_locale
        embed.set_footer(
            text=_("Current language set: {locale}").format(locale=current_locale)
        )

        locales = ", ".join(map(lambda l: f"`{l}`", i18n.locales))
        embed.description = locales
        await ctx.send(embed=embed)

    @language.command()
    @locale
    async def set(self, ctx, locale: valid_locale):
        _(
            """Update the bot language.

        `<locale>` - The locale code of the language to use.
        """
        )
        await self.set_locale(ctx.author.id, locale)
        i18n.current_locale.set(locale)
        self.bot.locales[ctx.author.id] = locale
        await ctx.send(
            _("Language successfully set to: `{locale}`").format(locale=locale)
        )


def setup(bot):
    bot.add_cog(Locale(bot))
