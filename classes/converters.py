from discord.ext import commands


class InvalidPlatform(commands.BadArgument):
    """Exception raised when an invalid platform is given."""

    def __init__(self):
        super().__init__(
            "Invalid platform. Supported platforms: `pc, psn, xbl and nintendo-switch`"
        )


class Platform(commands.Converter):
    async def convert(self, ctx, arg):
        x = arg.lower()
        if x not in ["pc", "psn", "xbl", "nintendo-switch", "switch", "nsw"]:
            raise InvalidPlatform()
        if x in ["nintendo-switch", "switch", "nsw"]:
            x = "nintendo-switch"
        return x


class Hero(commands.Converter):
    async def convert(self, ctx, arg):
        hero = arg.lower()
        # Advanced A.I. implementation
        if hero == "wreckingball":
            return "wreckingBall"
        elif hero in ["dva" "d.va"]:
            return "dVa"
        elif hero in ["soldier", "soldier-76"]:
            return "soldier76"
        elif hero == "lúcio":
            return "lucio"
        return hero
