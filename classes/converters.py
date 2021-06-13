from discord.ext import commands

from utils.i18n import _


class UnknownHero(commands.BadArgument):
    def __init__(self, hero):
        super().__init__(_("Unknown hero: **{hero}**.").format(hero=hero))


class Hero(commands.Converter):
    async def convert(self, ctx, argument):
        hero = argument.lower()
        if hero not in ctx.bot.hero_names:
            raise UnknownHero(hero)
        elif hero in ("soldier", "soldier-76"):
            return "soldier76"
        elif hero == "wreckingball":
            return "wreckingBall"
        elif hero in ("dva" "d.va"):
            return "dVa"
        elif hero == "lúcio":
            return "lucio"
        return hero


def valid_index(argument):
    if not argument.isdigit():
        raise commands.BadArgument(_("Index must be a number."))
    return int(argument)
