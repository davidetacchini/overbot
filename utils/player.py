import re

import discord

import config

SR = "<:sr:639897739920146437>"

ROLES = {
    "tank": "<:tank:645784573141319722>",
    "damage": "<:damage:645784543093325824>",
    "support": "<:support:645784563322191902>",
}


class PlayerException(Exception):
    """Base exception class for player.py."""

    pass


class NoStatistics(PlayerException):
    """Exception raised when a player has no statistics to display."""

    def __init__(self):
        super().__init__(
            "This profile has no quick play nor competitive statistics to display."
        )


class NoHeroStatistics(PlayerException):
    """Exception raised when a player has no quick play nor competitive stats for a given hero."""

    def __init__(self, player, hero):
        message = f"**{player}** has no quick play nor competitive statistics for **{hero}** to display."
        super().__init__(message)


class Player:

    __slots__ = ("data", "platform", "username", "color", "pages")

    def __init__(self, *, data: dict, platform: str, username: str):
        self.data = data
        self.platform = platform
        self.username = username

        self.color = config.main_color
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
    def has_statistics(self):
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

    def resolve_ratings(self):
        if not self.data["ratings"]:
            return None
        return self.data["ratings"]

    def get_ratings(self):
        embed = discord.Embed(color=self.color)
        embed.set_author(name=str(self), icon_url=self.avatar)

        player_ratings = self.resolve_ratings()

        if not player_ratings:
            embed.description = "This profile is unranked."
            return embed

        for key, value in player_ratings.items():
            embed.add_field(
                name=f"{ROLES.get(key)} **{key.upper()}**",
                value=f'{self.get_rating_icon(value["level"])} **{value["level"]}**{SR}',
            )
        embed.set_footer(
            text=f'Avarage: {self.data.get("rating")}',
            icon_url=self.data.get("ratingIcon"),
        )
        return embed

    def resolve_statistics(self, hero="allHeroes"):
        if not self.has_statistics:
            raise NoStatistics()

        # quickplay statistics
        q = self.data.get("quickPlayStats").get("careerStats").get(hero) or {}
        # competitive statistics
        c = self.data.get("competitiveStats").get("careerStats").get(hero) or {}

        if hero != "allHeroes" and not q and not c:
            raise NoHeroStatistics(str(self), hero)

        keys = list({*q, *c})
        keys.sort()

        for i, key in enumerate(keys):
            if not q.get(key) and not c.get(key):
                del keys[i]

        return keys, q, c

    def format_statistics(self, embed, key, quickplay, competitive):
        if quickplay and quickplay[key]:
            q_t = "\n".join(f"{k}: **{v}**" for k, v in quickplay[key].items())
            embed.add_field(name="Quickplay", value=self.add_space(q_t))
        if competitive and competitive[key]:
            c_t = "\n".join(f"{k}: **{v}**" for k, v in competitive[key].items())
            embed.add_field(name="Competitive", value=self.add_space(c_t))

    def get_statistics(self, ctx):
        keys, quickplay, competitive = self.resolve_statistics()

        for i, key in enumerate(keys, start=1):
            embed = discord.Embed(color=self.color)
            embed.title = self.format_key(key)
            embed.set_author(name=str(self), icon_url=self.avatar)
            embed.set_thumbnail(url=self.level_icon)
            embed.set_footer(text=f"Page {i}/{len(keys)}")
            self.format_statistics(embed, key, quickplay, competitive)
            self.pages.append(embed)
        return self.pages

    def get_hero(self, ctx, hero):
        keys, quickplay, competitive = self.resolve_statistics(hero)

        for i, key in enumerate(keys, start=1):
            embed = discord.Embed(color=self.color)
            embed.title = self.format_key(key)
            embed.set_author(name=str(self), icon_url=self.avatar)
            embed.set_thumbnail(url=ctx.bot.config.hero_url.format(hero.lower()))
            embed.set_footer(text=f"Page {i}/{len(keys)}")
            self.format_statistics(embed, key, quickplay, competitive)
            self.pages.append(embed)
        return self.pages

    def private(self, ctx):
        embed = discord.Embed(color=discord.Color.red())
        embed.title = "This profile is set to private"
        embed.description = (
            "Profiles are set to private by default."
            " You can modify this setting in Overwatch under `Options - Social`."
            " Please note that these changes may take effect after approximately 30 minutes."
        )
        embed.set_author(name=str(self), icon_url=self.avatar)
        return embed
