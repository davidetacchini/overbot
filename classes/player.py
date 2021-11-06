import re

from datetime import date

import discord

from utils import emojis

ROLES = {
    "tank": emojis.tank,
    "damage": emojis.damage,
    "support": emojis.support,
}


class PlayerException(Exception):

    pass


class NoStats(PlayerException):
    def __init__(self):
        super().__init__("This profile has no quick play nor competitive stats to display.")


class NoHeroStats(PlayerException):
    def __init__(self, hero):
        super().__init__(
            f"This profile has no quick play nor competitive stast for **{hero}** to display."
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

    @staticmethod
    def to_pascal(key):
        """From camel case to pascal case (testTest -> Test Test)."""
        return (
            re.sub("([a-z])([A-Z])", r"\g<1> \g<2>", key)
            .replace(" Avg Per10Min", "")
            .replace(" Most In Game", "")
            .title()
        )

    def format_key(self, key):
        if key == "best":
            return key.capitalize() + " (Most in game)"
        elif key == "average":
            return key.capitalize() + " (per 10 minutes)"
        return self.to_pascal(key)

    @staticmethod
    def get_rating_icon(rating):
        if 0 < rating < 1500:
            return emojis.bronze
        elif 1500 <= rating < 2000:
            return emojis.silver
        elif 2000 <= rating < 2500:
            return emojis.gold
        elif 2500 <= rating < 3000:
            return emojis.platinum
        elif 3000 <= rating < 3500:
            return emojis.diamond
        elif 3500 <= rating < 4000:
            return emojis.master
        return emojis.grand_master

    def is_private(self):
        return self.data["private"]

    def has_stats(self):
        return (
            self.data["quickPlayStats"]["careerStats"]
            or self.data["competitiveStats"]["careerStats"]
        )

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
            # Assuming a user uses `-profile rating` multiple times within
            # the same day, we don't want duplicate ratings. If only 1 rating
            # differs, then we insert the new ratings into the database.
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
            embed.description = "This profile is unranked."
            return embed

        for key, value in ratings.items():
            role_icon = ROLES.get(key)
            role_name = key.upper()
            rating_icon = self.get_rating_icon(value)
            embed.add_field(
                name=f"{role_icon} **{role_name}**",
                value=f"{rating_icon} **{value}**{emojis.sr}",
            )
        embed.set_footer(
            text="Average: {average}".format(average=self.data.get("rating")),
            icon_url=self.data.get("ratingIcon"),
        )

        if save:
            await self.save_ratings(ctx, profile_id=profile_id, **ratings)

        return embed

    def resolve_stats(self, hero):
        if not self.has_stats():
            raise NoStats()

        # quickplay stats
        q = self.data.get("quickPlayStats").get("careerStats").get(hero) or {}
        # competitive stats
        c = self.data.get("competitiveStats").get("careerStats").get(hero) or {}

        if hero != "allHeroes" and not q and not c:
            raise NoHeroStats(hero)

        keys = list({*q, *c})
        keys.sort()

        for i, key in enumerate(keys):
            if not q.get(key) and not c.get(key):
                del keys[i]

        return keys, q, c

    def format_stats(self, embed, key, quickplay, competitive):
        if quickplay and quickplay[key]:
            q_t = "\n".join(f"{k}: **{v}**" for k, v in quickplay[key].items())
            embed.add_field(name="Quickplay", value=self.to_pascal(q_t))
        if competitive and competitive[key]:
            c_t = "\n".join(f"{k}: **{v}**" for k, v in competitive[key].items())
            embed.add_field(name="Competitive", value=self.to_pascal(c_t))

    def get_stats(self, ctx, hero):
        keys, quickplay, competitive = self.resolve_stats(hero)

        for i, key in enumerate(keys, start=1):
            embed = discord.Embed(color=ctx.bot.color(ctx.author.id))
            embed.title = self.format_key(key)
            embed.set_author(name=str(self), icon_url=self.avatar)
            if hero == "allHeroes":
                embed.set_thumbnail(url=self.level_icon)
            else:
                embed.set_thumbnail(url=ctx.bot.config.hero_url.format(hero.lower()))
            embed.set_footer(text=f"Page {i}/{len(keys)}")
            self.format_stats(embed, key, quickplay, competitive)
            self.pages.append(embed)
        return self.pages

    def private(self):
        embed = discord.Embed(color=discord.Color.red())
        embed.title = "This profile is set to private"
        embed.description = (
            "Profiles are set to private by default."
            " You can modify this setting in Overwatch under `Options > Social`."
            " Please note that these changes may take effect after approximately 30 minutes."
        )
        embed.set_author(name=str(self), icon_url=self.avatar)
        return embed
