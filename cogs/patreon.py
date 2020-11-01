from discord.ext import commands

from utils.checks import is_donator


class Patreon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @is_donator()
    @commands.command()
    async def compare(self, ctx):
        pass


def setup(bot):
    bot.add_cog(Patreon(bot))
