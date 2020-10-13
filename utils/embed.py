import re

import discord

import config

SR = "<:sr:639897739920146437>"

ROLES = {
    "tank": "<:tank:645784573141319722>",
    "damage": "<:damage:645784543093325824>",
    "support": "<:support:645784563322191902>",
}


class NoStatistics(Exception):
    """Exception raised when a player has no statistics to display."""

    pass


class NoHeroStatistics(Exception):
    """Exception raised when a player has no quick play nor competitive stats
    for a given hero."""

    pass


class CustomEmbed:

    __slots__ = ("data", "platform", "name", "color")

    def __init__(self, **kwargs):
        self.data = kwargs.get("data", None)
        self.platform = kwargs.get("platform", None)
        self.name = kwargs.get("name", None)
        self.color = kwargs.get("color", config.main_color)

    @property
    def _name(self):
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
    def url(self):
        name = self.name.replace("#", "-").replace(" ", "%20")
        return config.overwatch["player"].format(self.platform, name)

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
        if rating > 0 and rating <= 1499:
            return "<:bronze:632281015863214096>"
        elif rating > 1499 and rating <= 1999:
            return "<:silver:632281054211997718>"
        elif rating > 1999 and rating <= 2499:
            return "<:gold:632281064596832278>"
        elif rating > 2499 and rating <= 2999:
            return "<:platinum:632281092875091998>"
        elif rating > 2999 and rating <= 3499:
            return "<:diamond:632281105571119105>"
        elif rating > 3499 and rating <= 3999:
            return "<:master:632281117394993163>"
        else:
            return "<:grandmaster:632281128966946826>"

    def format_key(self, key):
        return (
            self.add_space(key)
            if key not in ["best", "average"]
            else key.capitalize() + " (Most in game)"
            if key == "best"
            else key.capitalize() + " (per 10 minutes)"
        )

    def rank(self):
        """Returns players rank."""
        embed = discord.Embed(color=self.color)
        embed.set_author(name=self._name, icon_url=self.avatar, url=self.url)

        if not self.data["ratings"]:
            embed.description = "This profile is unranked."
            return embed

        for rate in self.data["ratings"].items():
            embed.add_field(
                name=f"{ROLES[rate[0]]} **{rate[0].upper()}**",
                value=f'{self.get_rating_icon(rate[1]["level"])} **{rate[1]["level"]}**{SR}',
            )
        return embed

    def has_statistics(self):
        if (
            self.data["quickPlayStats"]["careerStats"]
            or self.data["competitiveStats"]["careerStats"]
        ):
            return True
        return False

    def get_statistics(self, arg="allHeroes"):
        if not self.has_statistics():
            raise NoStatistics()

        # quickplay_keys and competitive_keys
        q_k = self.data.get("quickPlayStats").get("careerStats").get(arg) or {}
        c_k = self.data.get("competitiveStats").get("careerStats").get(arg) or {}

        if arg != "allHeroes":
            if not q_k and not c_k:
                raise NoHeroStatistics()

        keys = list(
            {
                *q_k,
                *c_k,
            }
        )
        keys.sort()
        quickplay, competitive = {}, {}

        for key in keys:
            quickplay[key] = q_k.get(key)
            competitive[key] = c_k.get(key)
        return keys, quickplay, competitive

    def format_statistics(self, embed, key, competitive, quickplay):
        if quickplay:
            if quickplay[key]:
                q_t = "\n".join(f"{k}: **{v}**" for k, v in quickplay[key].items())
                embed.add_field(name="Quickplay", value=self.add_space(q_t))
            else:
                embed.add_field(name="Quickplay", value="N/A")
        if competitive:
            if competitive[key]:
                c_t = "\n".join(f"{k}: **{v}**" for k, v in competitive[key].items())
                embed.add_field(name="Competitive", value=self.add_space(c_t))
            else:
                embed.add_field(name="Competitive", value="N/A")

    def statistics(self, ctx):
        """Returns competitive and/or quickplay player stats."""
        keys, quickplay, competitive = self.get_statistics()
        pages = []

        for i, key in enumerate(keys, start=1):
            embed = discord.Embed(color=self.color, timestamp=ctx.message.created_at)
            embed.title = self.format_key(key)
            embed.set_author(name=self._name, icon_url=self.avatar, url=self.url)
            embed.set_thumbnail(url=self.level_icon)
            embed.set_footer(text=f"Page {i}/{len(keys)}")
            self.format_statistics(embed, key, competitive, quickplay)
            pages.append(embed)
        return pages

    def hero(self, ctx, hero):
        keys, quickplay, competitive = self.get_statistics(hero)
        pages = []

        for i, key in enumerate(keys, start=1):
            embed = discord.Embed(color=self.color, timestamp=ctx.message.created_at)
            embed.title = self.format_key(key)
            embed.set_author(name=self._name, icon_url=self.avatar, url=self.url)
            embed.set_thumbnail(url=ctx.bot.config.hero_url.format(hero.lower()))
            embed.set_footer(text=f"Page {i}/{len(keys)}")
            self.format_statistics(embed, key, competitive, quickplay)
            pages.append(embed)
        return pages

    def private(self, ctx):
        """Returns an embed with private profile information."""
        embed = discord.Embed(color=0xFF3232, timestamp=ctx.message.created_at)
        embed.title = "This profile is set to private"
        embed.description = "Profiles are set to private by default. You can modify this setting in Overwatch under `Options - Social`. Please Note that these changes may take effect after approximately 30 minutes."
        embed.set_author(name=self._name, icon_url=self.avatar, url=self.url)
        return embed
