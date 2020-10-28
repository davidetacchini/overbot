from discord.ext import commands

# from utils.checks import is_donator, has_profile


class Patreon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # TODO: Add patreon commands


def setup(bot):
    bot.add_cog(Patreon(bot))
