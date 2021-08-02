import discord

from pygicord import Base, StopAction, StopPagination, control
from discord.ext import commands

from config import main_color
from utils.i18n import _


class HelpPaginator(Base):
    def __init__(self, pages):
        super().__init__(pages=pages, timeout=90)

    @control(emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}", position=0)
    async def first_page(self, payload):
        await self.show_page(0)

    @first_page.display_if
    def first_page_display_if(self):
        return len(self) > 3

    @control(emoji="\N{BLACK LEFT-POINTING TRIANGLE}", position=1)
    async def previous_page(self, payload):
        await self.show_page(self.index - 1)

    @control(emoji="\N{BLACK SQUARE FOR STOP}", position=2)
    async def stop(self, payload):
        raise StopPagination(StopAction.DELETE_MESSAGE)

    @control(emoji="\N{BLACK RIGHT-POINTING TRIANGLE}", position=3)
    async def next_page(self, payload):
        await self.show_page(self.index + 1)

    @control(emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}", position=4)
    async def last_page(self, payload):
        await self.show_page(len(self) - 1)

    @last_page.display_if
    def last_page_display_if(self):
        return len(self) > 3

    @control(emoji="\N{WHITE QUESTION MARK ORNAMENT}", position=5)
    async def show_help(self, payload):
        embed = discord.Embed(color=main_color)
        embed.title = _("Using the bot")
        embed.description = _("Welcome to the help page!")

        entries = (
            (_("<argument>"), _("This means the argument is **required**.")),
            (_("[argument]"), _("This means the argument is **optional**.")),
            (_("Note"), _("You **must not** include the brackets in the argument.")),
        )

        for name, value in entries:
            embed.add_field(name=name, value=value, inline=False)

        embed.set_footer(text=_("Press one of the arrows to go back."))
        await self.message.edit(content=None, embed=embed)


async def pager(entries, per_page):
    for x in range(0, len(entries), per_page):
        yield entries[x : x + per_page]


async def get_bot_help_pages(ctx, commands):
    description = _(
        "[Support]({support}) - [Commands]({website}) - [Translate]({github}) - [Premium]({premium})\n"
        'Use "{prefix}help [command]" for more info on a command\n'
        'Use "{prefix}help [category]" for more info on a category\n'
    ).format(
        support=ctx.bot.config.support,
        website=ctx.bot.config.website + "/commands",
        github=ctx.bot.config.github["repo"],
        premium=ctx.bot.config.premium,
        prefix=ctx.prefix,
    )

    cogs = sorted(commands.keys(), key=lambda c: c.qualified_name)
    pages = [p async for p in pager(cogs, 6)]

    all_pages = []
    for index, page in enumerate(pages, start=1):
        embed = discord.Embed(color=main_color)
        embed.title = _("{bot} Command List").format(bot=ctx.bot.user.display_name)
        embed.description = description

        for cog in page:
            commands_ = commands.get(cog)
            if commands_:
                value = ", ".join(map(lambda c: f"`{c}`", commands_))
                embed.add_field(name=cog.qualified_name, value=value)

        embed.set_footer(
            text=_("Page {current}/{total}").format(current=index, total=len(pages))
        )
        all_pages.append(embed)
    return all_pages


async def get_group_help_pages(ctx, help_command, group, commands):
    pages = [p async for p in pager(commands, 5)]

    all_pages = []
    for index, page in enumerate(pages, start=1):
        embed = discord.Embed(color=main_color)
        embed.title = _("{group} Commands").format(group=group.qualified_name)
        embed.description = group.description

        for command in page:
            signature = f"{command.qualified_name} {command.signature}"
            value = _(command.brief) or _("No help found...")
            embed.add_field(name=signature, value=value, inline=False)
            if (total := len(pages)) > 1:
                embed.set_author(
                    name=_(
                        "Page {current_page}/{total_pages} ({total_commands} commands)"
                    ).format(
                        current_page=index,
                        total_pages=total,
                        total_commands=len(commands),
                    )
                )
            embed.set_footer(
                text=_(
                    'Use "{prefix}help [command]" for more info on a command.'
                ).format(prefix=help_command.clean_prefix)
            )
        all_pages.append(embed)
    return all_pages


class CustomHelp(commands.HelpCommand):
    def __init__(self):
        command_attrs = {
            "brief": _("Shows help about the bot, a command, or a category."),
            "help": _("Shows help about the bot, a command, or a category."),
        }
        super().__init__(command_attrs=command_attrs)

    def get_command_signature(self, command):
        return f"{self.clean_prefix}{command.qualified_name} {command.signature}"

    def common_command_formatting(self, embeds, command):
        if not isinstance(embeds, list):
            embeds = [embeds]
        for embed in embeds:
            embed.title = self.get_command_signature(command)
            embed.description = _(command.help) or _("No help found...")
            if command.aliases:
                aliases = ", ".join(map(lambda a: f"`{a}`", command.aliases))
                embed.add_field(name=_("Aliases"), value=aliases)

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = self.context.bot
        filtered = await self.filter_commands(bot.commands, sort=True)

        commands = {}
        for command in filtered:
            if command.cog is None:
                continue
            try:
                commands[command.cog].append(command)
            except KeyError:
                commands[command.cog] = [command]

        pages = await get_bot_help_pages(ctx, commands)
        paginator = HelpPaginator(pages=pages)
        await paginator.start(ctx)

    async def send_cog_help(self, cog):
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        pages = await get_group_help_pages(self.context, self, cog, filtered)
        paginator = HelpPaginator(pages=pages)
        await paginator.start(self.context)

    async def send_group_help(self, group):
        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        filtered = await self.filter_commands(subcommands, sort=True)
        pages = await get_group_help_pages(self.context, self, group, filtered)
        self.common_command_formatting(pages, group)
        paginator = HelpPaginator(pages=pages)
        await paginator.start(self.context)

    async def send_command_help(self, command):
        embed = discord.Embed(color=main_color)
        self.common_command_formatting(embed, command)
        await self.context.send(embed=embed)


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.old_help_command = bot.help_command
        bot.help_command = CustomHelp()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self.old_help_command


def setup(bot):
    bot.add_cog(Help(bot))
