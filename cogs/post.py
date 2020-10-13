import json

from discord.ext import tasks, commands


class StatsPost(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update.start()

    @tasks.loop(minutes=30.0)
    async def update(self):
        """Updates Bot stats on Discord portals."""
        if self.bot.config.is_beta:
            return

        # POST stats on top.gg
        payload = {
            "server_count": len(self.bot.guilds),
            "shard_count": self.bot.shard_count,
        }

        topgg_headers = {"Authorization": self.bot.config.top_gg["token"]}

        await self.bot.session.post(
            self.bot.config.top_gg["url"], data=payload, headers=topgg_headers
        )

        # POST stats on discordbotlist.com
        dbl_payload = {"guilds": len(self.bot.guilds), "users": len(self.bot.users)}

        dbl_headers = {"Authorization": f'Bot {self.bot.config.dbl["token"]}'}

        await self.bot.session.post(
            self.bot.config.dbl["url"], data=dbl_payload, headers=dbl_headers
        )

        # POST stats on discord.bots.gg
        payload = json.dumps(
            {
                "guildCount": len(self.bot.guilds),
                "shardCount": self.bot.shard_count,
            }
        )

        headers = {
            "Authorization": self.bot.config.discord_bots["token"],
            "Content-Type": "application/json",
        }

        await self.bot.session.post(
            self.bot.config.discord_bots["url"], data=payload, headers=headers
        )

    def cog_unload(self):
        self.update.cancel()


def setup(bot):
    bot.add_cog(StatsPost(bot))
