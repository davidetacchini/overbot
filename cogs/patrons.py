import discord
from discord.ext import tasks, commands

from utils.checks import is_donator, has_profile
from utils.player import Player


class Patron(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.track_profile.start()

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

    @tasks.loop(hours=24.0)
    async def track_profile(self):
        await self.bot.wait_until_ready()
        if self.bot.is_ready():
            # don't send the message everytime the bot starts
            return

        profiles = await self.bot.pool.fetch(
            "SELECT id, platform, name FROM profile WHERE track <> false"
        )
        for profile in profiles:
            user = self.bot.get_user(profile["id"])
            data = await self.bot.data.Data(
                platform=profile["platform"], name=profile["name"]
            ).get()

            try:
                await user.send(
                    embed=Player(
                        data=data, platform=profile["platform"], name=profile["name"]
                    ).rank()
                )
            except discord.Forbidden:
                return

    def cog_unload(self):
        self.track_profile.cancel()


def setup(bot):
    bot.add_cog(Patron(bot))
