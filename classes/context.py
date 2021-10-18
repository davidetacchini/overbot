import re

from discord.ext import commands


class Context(commands.Context):
    CHECK = "\N{WHITE HEAVY CHECK MARK}"
    XMARK = "\N{CROSS MARK}"

    @property
    def clean_prefix(self):
        user = self.guild.me if self.guild else self.bot.user
        pattern = re.compile(r"<@!?%s>" % user.id)
        return pattern.sub("@%s" % user.display_name.replace("\\", r"\\"), self.prefix)

    def tick(self, opt, label=None):
        lookup = {
            True: "<:online:648186001361076243>",
            False: "<:dnd:648185968209428490>",
            None: "<:offline:648185992360099865>",
        }
        emoji = lookup.get(opt, "<:dnd:648185968209428490>")
        if label is not None:
            return f"{emoji}: {label}"
        return emoji
