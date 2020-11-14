from discord.ext import commands

PLATFORMS = [
    "pc",
    "ps",
    "psn",
    "play",
    "playstation",
    "xbox",
    "xbl",
    "nintendo-switch",
    "switch",
    "nsw",
]
XBOX = ["xbl", "xbox"]
PLAYSTATION = ["ps", "psn", "play", "playstation"]
NINTENDO_SWITCH = ["nsw", "switch", "nintendo-switch"]


class InvalidPlatform(commands.BadArgument):
    """Exception raised when an invalid platform is given."""

    def __init__(self):
        super().__init__("Invalid platform.")


class Platform(commands.Converter):
    async def convert(self, ctx, arg):
        platform = arg.lower()
        if platform not in PLATFORMS:
            raise InvalidPlatform()
        if platform in PLAYSTATION:
            return "psn"
        if platform in XBOX:
            return "xbl"
        if platform in NINTENDO_SWITCH:
            return "nintendo-switch"
        return platform


class Hero(commands.Converter):
    async def convert(self, ctx, arg):
        hero = arg.lower()
        # Advanced A.I. implementation
        if hero in ["soldier", "soldier-76"]:
            return "soldier76"
        elif hero == "wreckingball":
            return "wreckingBall"
        elif hero in ["dva" "d.va"]:
            return "dVa"
        elif hero == "lúcio":
            return "lucio"
        return hero


class HeroCategory(commands.Converter):
    async def convert(self, ctx, arg):
        category = arg.lower()
        if category in ["heal", "healer"]:
            return "support"
        elif category == "dps":
            return "damage"
        return category


class MapCategory(commands.Converter):
    async def convert(self, ctx, arg):
        return arg.lower()
