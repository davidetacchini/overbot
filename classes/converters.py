from discord.ext import commands

from utils.i18n import _


class Hero(commands.Converter):
    async def convert(self, ctx, argument):
        _hero = argument.lower()
        aliases = {
            "soldier": "soldier76",
            "soldier-76": "soldier76",
            "wreckingball": "wreckingBall",
            "dva": "dVa",
            "d.va": "dVa",
            "lúcio": "lucio",
        }

        hero = aliases.get(_hero)
        if hero is None:
            if _hero not in ctx.bot.hero_names:
                raise commands.BadArgument(
                    _("Unknown hero: **{hero}**.").format(hero=hero)
                )
            else:
                return _hero
        else:
            return hero


def valid_index(argument):
    if not argument.isdigit():
        raise commands.BadArgument(_("Index must be a number."))
    return int(argument)
