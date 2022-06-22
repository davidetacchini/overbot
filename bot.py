import os
import sys

import asyncpg
import discord

from aiohttp import ClientSession
from discord import app_commands
from termcolor import colored
from discord.ext import commands

import config

from utils import emojis
from classes.ui import PromptView
from utils.time import human_timedelta
from utils.errors import error_handler
from utils.scrape import get_overwatch_maps, get_overwatch_heroes
from classes.paginator import Paginator

if sys.platform == "linux":
    import uvloop

    uvloop.install()


class OverBot(commands.AutoShardedBot):
    """Custom bot class for OverBot."""

    def __init__(self, **kwargs):
        super().__init__(
            command_prefix=config.default_prefix,
            allowed_mentions=discord.AllowedMentions.none(),
            **kwargs,
        )
        self.config = config
        self.sloc: int = 0

        # caching
        self.premiums: dict[int, bool] = {}
        self.embed_colors: dict[int, int] = {}
        self.heroes: dict[int, dict] = {}
        self.maps: list[dict] = []

        self.normal_cooldown: app_commands.Cooldown = app_commands.Cooldown(1, config.BASE_COOLDOWN)
        self.premium_cooldown: app_commands.Cooldown = app_commands.Cooldown(
            1, config.PREMIUM_COOLDOWN
        )

        self.TEST_GUILD: discord.Object = discord.Object(config.test_guild_id)

    @property
    def version(self) -> str:
        return config.version

    @property
    def debug(self) -> bool:
        return config.DEBUG

    @property
    def webhook(self) -> discord.Webhook:
        wh_id, wh_token = (config.webhook["id"], config.webhook["token"])
        return discord.Webhook.partial(id=wh_id, token=wh_token, session=self.session)

    def color(self, member_id: None | int = None) -> int:
        return self.embed_colors.get(member_id, config.main_color)

    def get_uptime(self, *, brief: bool = False) -> str:
        return human_timedelta(self.uptime, accuracy=None, brief=brief, suffix=False)

    async def total_commands(self) -> int:
        total_commands = await self.pool.fetchval("SELECT COUNT(*) FROM command;")
        return total_commands + config.old_commands_count

    async def on_message(self, message: discord.Message) -> None:
        if not self.is_ready():
            return
        await self.process_commands(message)

    async def paginate(
        self, entries: list[discord.Embed | str], *, interaction: discord.Interaction, **kwargs
    ) -> None:
        paginator = Paginator(entries, interaction=interaction, **kwargs)
        await paginator.start()

    async def prompt(
        self, interaction: discord.Interaction, payload: dict[None | str, None | discord.Embed]
    ) -> bool:
        if isinstance(payload, str):
            kwargs = {"content": payload, "embed": None}
        elif isinstance(payload, discord.Embed):
            kwargs = {"content": None, "embed": payload}
        view = PromptView(author_id=interaction.user.id)
        if interaction.response.is_done():
            view.message = await interaction.followup.send(**kwargs, view=view)
        else:
            view.message = await interaction.response.send_message(**kwargs, view=view)
        await view.wait()
        return view.value

    def tick(self, opt: bool) -> discord.PartialEmoji:
        lookup = {
            True: emojis.online,
            False: emojis.dnd,
            None: emojis.offline,
        }
        return lookup.get(opt, emojis.dnd)

    async def get_or_fetch_member(self, member_id: int) -> None | discord.Member:
        guild = self.get_guild(config.support_server_id)

        member = guild.get_member(member_id)
        if member is not None:
            return member

        shard = self.get_shard(guild.shard_id)
        if shard.is_ws_ratelimited():
            try:
                member = await guild.fetch_member(member_id)
            except discord.HTTPException:
                return None
            else:
                return member

        members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
        if not members:
            return None
        return members[0]

    def compute_sloc(self) -> None:
        """Compute source lines of code."""
        for root, dirs, files in os.walk(os.getcwd()):
            [dirs.remove(d) for d in list(dirs) if d == "env"]
            for file in files:
                if file.endswith(".py"):
                    with open(f"{root}/{file}") as fp:
                        self.sloc += len(fp.readlines())

    def member_is_premium(self, member_id: int, guild_id: int):
        """Check for a member/guild to be premium."""
        to_check = (member_id, guild_id)
        return any(x in self.premiums for x in to_check)

    def get_profiles_limit(self, interaction: discord.Interaction, member_id: int) -> int:
        guild_id = interaction.guild.id if interaction.guild is not None else 0
        if not self.member_is_premium(member_id, guild_id):
            return config.BASE_PROFILES_LIMIT
        return config.PREMIUM_PROFILES_LIMIT

    async def cache_premiums(self) -> None:
        query = """SELECT id
                   FROM member
                   WHERE member.premium = true
                   UNION
                   SELECT id
                   FROM server
                   WHERE server.premium = true;
                """
        ids = await self.pool.fetch(query)
        self.premiums = {i["id"] for i in ids}

    async def cache_heroes(self) -> None:
        self.heroes = await get_overwatch_heroes()

    async def cache_maps(self) -> None:
        self.maps = await get_overwatch_maps()

    async def cache_embed_colors(self) -> None:
        embed_colors = {}
        query = "SELECT id, embed_color FROM member WHERE embed_color IS NOT NULL;"
        colors = await self.pool.fetch(query)
        for member_id, color in colors:
            embed_colors[member_id] = color
        self.embed_colors = embed_colors

    async def setup_hook(self) -> None:
        self.session = ClientSession()
        self.pool = await asyncpg.create_pool(**config.database, max_size=20, command_timeout=60.0)

        self.compute_sloc()
        # caching
        await self.cache_premiums()
        await self.cache_embed_colors()
        await self.cache_heroes()
        await self.cache_maps()

        for extension in os.listdir("cogs"):
            if extension.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{extension[:-3]}")
                except Exception as e:
                    print(f"[{colored('ERROR', 'red')}]{extension:20} failed its loading!\n[{e}]")
                else:
                    print(f"[{colored('OK', 'green')}]{extension:20} successfully loaded")

        self.tree.on_error = error_handler

        if self.debug:
            self.tree.copy_global_to(guild=self.TEST_GUILD)
            await self.tree.sync(guild=self.TEST_GUILD)
        else:
            await self.tree.sync()

    async def close(self) -> None:
        await super().close()
        await self.session.close()
        await self.pool.close()


def main() -> None:
    intents = discord.Intents.none()
    intents.guilds = True
    intents.members = True
    intents.reactions = True
    intents.messages = True

    bot = OverBot(
        activity=discord.Game(name="Starting..."),
        status=discord.Status.dnd,
        intents=intents,
        application_id=550359245963526194,
        chunk_guilds_at_startup=False,
        guild_ready_timeout=5,
    )

    bot.run(bot.config.token, reconnect=True)


if __name__ == "__main__":
    main()
