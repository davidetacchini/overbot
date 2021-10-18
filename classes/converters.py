from discord.ext import commands


class Hero(commands.Converter):
    async def convert(self, ctx, argument):
        hero_ = argument.lower()
        aliases = {
            "soldier": "soldier76",
            "soldier-76": "soldier76",
            "wreckingball": "wreckingBall",
            "dva": "dVa",
            "d.va": "dVa",
            "lúcio": "lucio",
        }

        hero = aliases.get(hero_)
        if hero is None:
            if hero_ not in ctx.bot.hero_names:
                raise commands.BadArgument(f"Unknown hero: **{argument}**.")
            else:
                return hero_
        else:
            return hero
