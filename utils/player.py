import re
from datetime import date

import discord

from utils.i18n import _

SR = "<:sr:639897739920146437>"

ROLES = {
    "tank": "<:tank:645784573141319722>",
    "damage": "<:damage:645784543093325824>",
    "support": "<:support:645784563322191902>",
}


class PlayerException(Exception):
    """Base exception class for player.py."""

    pass


class NoStats(PlayerException):
    """Exception raised when a player has no stats to display."""

    def __init__(self):
        super().__init__(
            _("This profile has no quick play nor competitive stats to display.")
        )


class NoHeroStats(PlayerException):
    """Exception raised when a player has no quick play nor competitive stats for a given hero."""

    def __init__(self, player, hero):
        super().__init__(
            _(
                "**{player}** has no quick play nor competitive stast for **{hero}** to display."
            ).format(player=player, hero=hero)
        )


class Player:

    __slots__ = ("data", "platform", "username", "pages")

    def __init__(self, data: dict, *, platform: str, username: str):
        self.data = data
        self.platform = platform
        self.username = username

        self.pages = []

    def __str__(self):
        return self.data["name"]

    @property
    def avatar(self):
        return self.data["icon"]

    @property
    def level_icon(self):
        return self.data["levelIcon"]

    @property
    def is_private(self):
        return self.data["private"]

    @property
    def has_stats(self):
        return (
            self.data["quickPlayStats"]["careerStats"]
            or self.data["competitiveStats"]["careerStats"]
        )

    @staticmethod
    def add_space(key):
        """From camel case to title (testTest -> Test Test)."""
        return (
            re.sub("([a-z])([A-Z])", r"\g<1> \g<2>", key)
            .replace(" Avg Per10Min", "")
            .replace(" Most In Game", "")
            .title()
        )

    @staticmethod
    def get_rating_icon(rating):
        if rating > 0 and rating < 1500:
            return "<:bronze:632281015863214096>"
        elif rating >= 1500 and rating < 2000:
            return "<:silver:632281054211997718>"
        elif rating >= 2000 and rating < 2500:
            return "<:gold:632281064596832278>"
        elif rating >= 2500 and rating < 3000:
            return "<:platinum:632281092875091998>"
        elif rating >= 3000 and rating < 3500:
            return "<:diamond:632281105571119105>"
        elif rating >= 3500 and rating < 4000:
            return "<:master:632281117394993163>"
        else:
            return "<:grandmaster:632281128966946826>"

    def format_key(self, key):
        if key == "best":
            return key.capitalize() + " (Most in game)"
        elif key == "average":
            return key.capitalize() + " (per 10 minutes)"
        else:
            return self.add_space(key)

    async def save_ratings(self, ctx, *, profile_id, **kwargs):
        tank = kwargs.get("tank", 0)
        damage = kwargs.get("damage", 0)
        support = kwargs.get("support", 0)

        query = """SELECT tank, damage, support
                   FROM rating
                   INNER JOIN profile
                           ON profile.id = rating.profile_id
                   WHERE profile.id = $1
                   AND rating.date = $2;
                """

        requested_at = date.today()
        roles = await ctx.bot.pool.fetch(query, profile_id, requested_at)

        if roles:
            # Assuming a user uses `-profile rating` multiple times within the same day,
            # we don't want duplicate ratings. If only 1 rating differs, then we
            # insert the new ratings into the database.
            all_equals = False
            for t, d, s in roles:
                if t == tank and d == damage and s == support:
                    all_equals = True

        if not roles or not all_equals:
            query = "INSERT INTO rating(tank, damage, support, profile_id) VALUES($1, $2, $3, $4);"
            await ctx.bot.pool.execute(query, tank, damage, support, profile_id)

    def resolve_ratings(self):
        if not self.data["ratings"]:
            return None
        ratings = {}
        for key, value in self.data["ratings"].items():
            ratings[key.lower()] = value["level"]
        return ratings

    async def get_ratings(self, ctx, *, save=False, profile_id=None):
        embed = discord.Embed(color=ctx.bot.color(ctx.author.id))
        embed.set_author(name=str(self), icon_url=self.avatar)

        ratings = self.resolve_ratings()

        if not ratings:
            embed.description = _("This profile is unranked.")
            return embed

        for key, value in ratings.items():
            embed.add_field(
                name=f"{ROLES.get(key)} **{key.upper()}**",
                value=f"{self.get_rating_icon(value)} **{value}**{SR}",
            )
        embed.set_footer(
            text=_("Average: {average}").format(average=self.data.get("rating")),
            icon_url=self.data.get("ratingIcon"),
        )

        if save:
            await self.save_ratings(ctx, profile_id=profile_id, **ratings)

        return embed

    def resolve_stats(self, hero="allHeroes"):
        if not self.has_stats:
            raise NoStats()

        # quickplay stats
        q = self.data.get("quickPlayStats").get("careerStats").get(hero) or {}
        # competitive stats
        c = self.data.get("competitiveStats").get("careerStats").get(hero) or {}

        if hero != "allHeroes" and not q and not c:
            raise NoHeroStats(str(self), hero)

        keys = list({*q, *c})
        keys.sort()

        for i, key in enumerate(keys):
            if not q.get(key) and not c.get(key):
                del keys[i]

        return keys, q, c

    def format_stats(self, embed, key, quickplay, competitive):
        if quickplay and quickplay[key]:
            q_t = "\n".join(f"{k}: **{v}**" for k, v in quickplay[key].items())
            embed.add_field(name=_("Quickplay"), value=self.add_space(q_t))
        if competitive and competitive[key]:
            c_t = "\n".join(f"{k}: **{v}**" for k, v in competitive[key].items())
            embed.add_field(name=_("Competitive"), value=self.add_space(c_t))

    def get_stats(self, ctx):
        keys, quickplay, competitive = self.resolve_stats()

        for i, key in enumerate(keys, start=1):
            embed = discord.Embed(color=ctx.bot.color(ctx.author.id))
            embed.title = self.format_key(key)
            embed.set_author(name=str(self), icon_url=self.avatar)
            embed.set_thumbnail(url=self.level_icon)
            embed.set_footer(
                text=_("Page {current}/{total}").format(current=i, total=len(keys))
            )
            self.format_stats(embed, key, quickplay, competitive)
            self.pages.append(embed)
        return self.pages

    def get_hero(self, ctx, hero):
        keys, quickplay, competitive = self.resolve_stats(hero)

        for i, key in enumerate(keys, start=1):
            embed = discord.Embed(color=ctx.bot.color(ctx.author.id))
            embed.title = self.format_key(key)
            embed.set_author(name=str(self), icon_url=self.avatar)
            embed.set_thumbnail(url=ctx.bot.config.hero_url.format(hero.lower()))
            embed.set_footer(
                text=_("Page {current}/{total}").format(current=i, total=len(keys))
            )
            self.format_stats(embed, key, quickplay, competitive)
            self.pages.append(embed)
        return self.pages

    def private(self):
        embed = discord.Embed(color=discord.Color.red())
        embed.title = _("This profile is set to private")
        embed.description = _(
            "Profiles are set to private by default."
            " You can modify this setting in Overwatch under `Options - Social`."
            " Please note that these changes may take effect after approximately 30 minutes."
        )
        embed.set_author(name=str(self), icon_url=self.avatar)
        return embed
