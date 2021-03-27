import discord
from discord.ext import commands

from utils import i18n
from utils.i18n import _, locale
from utils.paginator import ChooseLocale


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
        embed = discord.Embed(color=self.bot.get_color(ctx.author.id))
        embed.title = _("Available Languages")
        current_locale = self.bot.locales[ctx.author.id] or i18n.current_locale
        embed.set_footer(
            text=_("Current language set: {locale}").format(locale=current_locale)
        )

        description = []
        for _locale in i18n.locales:
            description.append(f"`{_locale}`")

        embed.description = ", ".join(description)
        await ctx.send(embed=embed)

    @language.command()
    @locale
    async def set(self, ctx):
        _("""Update the bot language.""")
        title = _("Set the bot language")
        locale = await ChooseLocale(title=title).start(ctx)

        if not locale:
            return
        try:
            await self.set_locale(ctx.author.id, locale)
            i18n.current_locale.set(locale)
            self.bot.locales[ctx.author.id] = locale
        except Exception as e:
            await ctx.send(embed=self.bot.embed_exception(e))
        else:
            await ctx.send(
                _("Language successfully set to: `{locale}`").format(locale=locale)
            )


def setup(bot):
    bot.add_cog(Locale(bot))
