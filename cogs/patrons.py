from discord.ext import commands

from utils.checks import is_donator, has_profile


class Patron(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @is_donator()
    @has_profile()
    @commands.command(brief="premium")
    async def track(self, ctx):
        """Set up your profile to be tracked and receive your ranks updated every 24 hours in your DMs."""
        async with ctx.typing():
            await self.bot.pool.execute(
                "UPDATE profile SET track=true WHERE id=$1", ctx.author.id
            )
            await ctx.send(
                "Your profile has been successfully linked to be tracked. You will receive your ranks information every 24 hours in your DMs. Make sure you can receive DM messages from me!"
            )

    @is_donator()
    @has_profile()
    @commands.command(brief="premium")
    async def untrack(self, ctx):
        """Remove your profile from monitoring."""
        if not await ctx.confirm(
            "Are you sure you want to remove your profile from being monitored?"
        ):
            return

        await self.bot.pool.execute(
            "UPDATE profile SET track=false WHERE id=$1", ctx.author.id
        )
        await ctx.send("Your profile will no longer be monitored.")


def setup(bot):
    bot.add_cog(Patron(bot))
