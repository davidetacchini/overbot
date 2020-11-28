from discord.ext import commands


class Trivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def trivia(self, ctx):
        pass


def setup(bot):
    bot.add_cog(Trivia(bot))
