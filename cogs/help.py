import asyncio

from contextlib import suppress

import discord

from discord.ext import menus, commands

from config import main_color
from utils.i18n import _


class HelpMenu(menus.MenuPages):
    def __init__(self, source):
        super().__init__(source=source, timeout=90.0, check_embeds=True)

    async def finalize(self, timed_out):
        with suppress(discord.HTTPException):
            if timed_out:
                await self.message.clear_reactions()
            else:
                await self.message.delete()

    def _skip_double_triangle_buttons(self):
        max_pages = self._source.get_max_pages()
        if max_pages is None:
            return True
        return max_pages <= 2

    @menus.button(
        "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
        position=menus.First(0),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_first_page(self, payload):
        await self.show_page(0)

    @menus.button("\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f", position=menus.First(1))
    async def go_to_previous_page(self, payload):
        await self.show_checked_page(self.current_page - 1)

    @menus.button("\N{BLACK SQUARE FOR STOP}\ufe0f", position=menus.Last(0))
    async def stop_pages(self, payload):
        self.stop()

    @menus.button("\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f", position=menus.Last(1))
    async def go_to_next_page(self, payload):
        await self.show_checked_page(self.current_page + 1)

    @menus.button(
        "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
        position=menus.Last(2),
        skip_if=_skip_double_triangle_buttons,
    )
    async def go_to_last_page(self, payload):
        await self.show_page(self._source.get_max_pages() - 1)

    @menus.button("\N{WHITE QUESTION MARK ORNAMENT}", position=menus.Last(3))
    async def show_bot_help(self, payload):
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

        embed.set_footer(
            text=_("We were on page {current_page} before this message.").format(
                current_page=self.current_page + 1
            )
        )
        await self.message.edit(embed=embed)

        async def go_back_to_current_page():
            await asyncio.sleep(30.0)
            with suppress(discord.HTTPException, discord.NotFound):
                await self.show_page(self.current_page)

        self.bot.loop.create_task(go_back_to_current_page())


class BotHelp(menus.ListPageSource):
    def __init__(self, bot, help_command, commands):
        super().__init__(
            entries=sorted(commands.keys(), key=lambda c: c.qualified_name), per_page=6
        )
        self.bot = bot
        self.commands = commands
        self.help_command = help_command
        self.prefix = help_command.clean_prefix

    async def format_page(self, menu, cogs):
        description = _(
            "[Support server]({support}) - [View commands online]({website}) - [Help translating]({github})\n"
            'Use "{prefix}help [command]" for more info on a command\n'
            'Use "{prefix}help [category]" for more info on a category'
        ).format(
            support=self.bot.config.support,
            website=self.bot.config.website + "/commands",
            github=self.bot.config.github["repo"],
            prefix=self.prefix,
        )

        embed = discord.Embed(color=main_color)
        embed.title = _("Help")
        embed.description = description

        for cog in cogs:
            commands = self.commands.get(cog)
            if commands:
                value = ", ".join(map(lambda c: f"`{c}`", commands))
                embed.add_field(name=cog.qualified_name, value=value)

        maximum = self.get_max_pages()
        embed.set_footer(
            text=_("Page {current_page}/{maximum}").format(
                current_page=menu.current_page + 1, maximum=maximum
            )
        )
        return embed


class GroupHelp(menus.ListPageSource):
    def __init__(self, group, commands, *, prefix):
        super().__init__(entries=commands, per_page=5)
        self.group = group
        self.prefix = prefix
        self.title = _("{group} Commands").format(group=self.group.qualified_name)
        self.description = self.group.description

    async def format_page(self, menu, commands):
        embed = discord.Embed(color=main_color)
        embed.title = self.title
        embed.description = _(self.description)

        for command in commands:
            signature = f"{command.qualified_name} {command.signature}"
            embed.add_field(
                name=signature,
                value=_(command.short_doc) or _("No help found..."),
                inline=False,
            )

        maximum = self.get_max_pages()
        if maximum > 1:
            embed.set_author(
                name=_(
                    "Page {current_page}/{maximum} ({total_entries} commands)"
                ).format(
                    current_page=menu.current_page + 1,
                    maximum=maximum,
                    total_entries=len(self.entries),
                )
            )

        embed.set_footer(
            text=_('Use "{prefix}help [command]" for more info on a command.').format(
                prefix=self.prefix
            )
        )
        return embed


class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        command_attrs = dict(
            help=_("Shows help about the bot, a command, or a category."),
        )
        super().__init__(command_attrs=command_attrs)

    def get_command_signature(self, command):
        parent = command.full_parent_name
        fmt = command.name if not parent else f"{parent} {command.name}"
        return f"{self.clean_prefix}{fmt} {command.signature}"

    def common_command_formatting(self, embed, command):
        embed.title = self.get_command_signature(command)
        if command.help:
            embed.description = _(command.help)
        else:
            embed.description = _("No help found...")
        if command.aliases and not isinstance(embed, GroupHelp):
            aliases = ", ".join(map(lambda a: f"`{a}`", command.aliases))
            embed.add_field(name=_("Aliases"), value=aliases)

    async def send_bot_help(self, mapping):
        bot = self.context.bot
        entries = await self.filter_commands(bot.commands, sort=True)

        all_commands = {}
        for command in entries:
            if command.cog is None:
                continue
            try:
                all_commands[command.cog].append(command)
            except KeyError:
                all_commands[command.cog] = [command]

        menu = HelpMenu(BotHelp(bot, self, all_commands))
        await menu.start(self.context)

    async def send_command_help(self, command):
        embed = discord.Embed(color=main_color)
        self.common_command_formatting(embed, command)
        await self.context.send(embed=embed)

    async def send_cog_help(self, cog):
        entries = await self.filter_commands(cog.get_commands(), sort=True)
        menu = HelpMenu(GroupHelp(cog, entries, prefix=self.clean_prefix))
        await menu.start(self.context)

    async def send_group_help(self, group):
        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        entries = await self.filter_commands(subcommands, sort=True)
        if len(entries) == 0:
            return await self.send_command_help(group)

        source = GroupHelp(group, entries, prefix=self.clean_prefix)
        self.common_command_formatting(source, group)
        menu = HelpMenu(source)
        await menu.start(self.context)


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.old_help_command = bot.help_command
        bot.help_command = CustomHelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self.old_help_command


def setup(bot):
    bot.add_cog(Help(bot))
