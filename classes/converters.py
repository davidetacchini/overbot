from discord.ext import commands

PC = ("pc", "bnet")
XBOX = ("xbl", "xbox")
PLAYSTATION = ("ps", "psn", "play", "playstation")
NINTENDO_SWITCH = ("nsw", "switch", "nintendo-switch")
PLATFORMS = XBOX + PLAYSTATION + NINTENDO_SWITCH + PC


class InvalidPlatform(commands.BadArgument):
    """Exception raised when an invalid platform is given."""

    def __init__(self, ctx):
        prefix = ctx.prefix
        command = ctx.command.qualified_name
        super().__init__(
            f'Invalid platform. Use "{prefix}help {command}" for more info.'
        )


class InvalidHero(commands.BadArgument):
    """Exception raised when an invalid hero is given."""

    def __init__(self, hero):
        super().__init__(f"Hero **{hero}** doesn't exist.")


class Platform(commands.Converter):
    async def convert(self, ctx, platform):
        platform = platform.lower()
        if platform not in PLATFORMS:
            raise InvalidPlatform(ctx)
        elif platform in PC:
            return "pc"
        elif platform in PLAYSTATION:
            return "psn"
        elif platform in XBOX:
            return "xbl"
        elif platform in NINTENDO_SWITCH:
            return "nintendo-switch"


class Hero(commands.Converter):
    async def convert(self, ctx, hero):
        hero = hero.lower()
        if hero not in ctx.bot.heroes:
            raise InvalidHero(hero)
        # Advanced A.I. implementation
        elif hero in ("soldier", "soldier-76"):
            return "soldier76"
        elif hero == "wreckingball":
            return "wreckingBall"
        elif hero in ("dva" "d.va"):
            return "dVa"
        elif hero == "lúcio":
            return "lucio"
        return hero


class HeroCategory(commands.Converter):
    async def convert(self, ctx, category):
        category = category.lower()
        if category in ("heal", "healer"):
            return "support"
        elif category == "dps":
            return "damage"
        return category


class MapCategory(commands.Converter):
    async def convert(self, ctx, arg):
        return arg.lower()
