import re

from discord.ext import commands

from utils import emojis


class Context(commands.Context):
    @property
    def clean_prefix(self):
        user = self.guild.me if self.guild else self.bot.user
        pattern = re.compile(r"<@!?%s>" % user.id)
        return pattern.sub("@%s" % user.display_name.replace("\\", r"\\"), self.prefix)

    def tick(self, opt, label=None):
        lookup = {
            True: emojis.online,
            False: emojis.dnd,
            None: emojis.offline,
        }
        emoji = lookup.get(opt, emojis.dnd)
        if label is not None:
            return f"{emoji}: {label}"
        return emoji
