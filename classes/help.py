# partially inspired by https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/meta.py
from typing import Mapping

import discord

from discord.ext import commands

from utils.funcs import chunker
from classes.context import Context
from classes.paginator import Paginator

PagesT = list[discord.Embed | str]
MappingT = Mapping[commands.Cog, list[commands.Command]]


class HelpSelect(discord.ui.Select):
    def __init__(self, bot: commands.AutoShardedBot, mapping: MappingT) -> None:
        super().__init__(placeholder="Select a category...")
        self.bot = bot
        self.mapping = mapping
        self.__fill_options()

    def __fill_options(self) -> None:
        self.add_option(label="Homepage", value="homepage")
        for cog, commands_ in self.mapping.items():
            unwanted_cogs = ["Owner"]
            if cog is None or len(commands_) == 0 or cog.qualified_name in unwanted_cogs:
                continue
            self.add_option(label=cog.qualified_name)

    async def callback(self, interaction: discord.Interaction) -> None:
        value = self.values[0]
        if value == "homepage":
            await self.view.rebind(get_bot_homepage(self.view.ctx), interaction)
        else:
            cog = self.bot.get_cog(value)
            if cog is None:
                return await interaction.response.send_message(
                    "Somehow this category does not exists.", ephemeral=True
                )
            commands = [c for c in cog.walk_commands()]
            if not commands:
                return await interaction.response.send_message(
                    "This category has no commands to show.", ephemeral=True
                )
            pages = await get_group_help_pages(self.view.ctx, cog, commands)
            await self.view.rebind(pages, interaction)


class HelpPaginator(Paginator):
    def add_categories(self, mapping: MappingT) -> None:
        self.clear_items()
        self.add_item(HelpSelect(self.ctx.bot, mapping))
        self.fill_items()

    async def rebind(self, pages: PagesT, interaction: discord.Interaction) -> None:
        self.pages = pages
        self.current = 0
        kwargs = self._get_kwargs_from_page(self.pages[self.current])
        self._update_labels(0)
        await interaction.response.edit_message(**kwargs, view=self)


def get_bot_homepage(ctx: "Context") -> list[discord.Embed]:
    pages = []

    # page 1
    embed = discord.Embed(color=ctx.bot.color(ctx.author.id))
    embed.title = "Bot Help"
    embed.description = (
        "Welcome to the OverBot help page!\n\n"
        'Use "{prefix}help [command]" for more info on a command\n'
        'Use "{prefix}help [category]" for more info on a category\n'
        "Use the dropdown menu below to select a category."
    ).format(prefix=ctx.prefix)

    value = "[Support]({support}) - [Commands]({website}) - [GitHub]({github}) - [Premium]({premium})\n".format(
        support=ctx.bot.config.support,
        website=ctx.bot.config.website + "/commands",
        github=ctx.bot.config.github["repo"],
        premium=ctx.bot.config.premium,
    )
    embed.add_field(name="Links", value=value)
    pages.append(embed)

    # page 2
    embed = discord.Embed(color=ctx.bot.color(ctx.author.id))
    embed.title = "Using the bot"

    entries = (
        ("<argument>", "This means the argument is **required**."),
        ("[argument]", "This means the argument is **optional**."),
        ("Note", "You **must not** include the brackets in the argument."),
    )

    for name, value in entries:
        embed.add_field(name=name, value=value, inline=False)

    pages.append(embed)

    return pages


async def get_group_help_pages(
    ctx: "Context", group: commands.Cog | commands.Group, mapping: MappingT
):
    chunks = [c async for c in chunker(mapping, per_page=5)]

    pages = []
    for index, chunk in enumerate(chunks, start=1):
        embed = discord.Embed(color=ctx.bot.color(ctx.author.id))
        embed.title = f"{group.qualified_name} Commands"
        embed.description = group.description

        for command in chunk:
            signature = f"{command.qualified_name} {command.signature}"
            if command.extras.get("premium"):
                signature += " :star:"
            value = command.short_doc or "No help found..."
            embed.add_field(name=signature, value=value, inline=False)
            if (total := len(pages)) > 1:
                embed.set_author(
                    name="Page {current_page}/{total_pages} ({total_commands} commands)".format(
                        current_page=index,
                        total_pages=total,
                        total_commands=len(mapping),
                    )
                )
            embed.set_footer(
                text='Use "{prefix}help [command]" for more info on a command.'.format(
                    prefix=ctx.clean_prefix
                )
            )
        pages.append(embed)
    return pages


class CustomHelp(commands.HelpCommand):
    def __init__(self) -> None:
        command_attrs = {
            "help": "Shows help about the bot, a command, or a category.",
        }
        super().__init__(command_attrs=command_attrs)

    def get_command_signature(self, command: commands.Command) -> str:
        return f"{self.context.clean_prefix}{command.qualified_name} {command.signature}"

    def common_command_formatting(
        self, embeds: list[discord.Embed], command: commands.Command
    ) -> None:
        if not isinstance(embeds, list):
            embeds = [embeds]
        for embed in embeds:
            embed.title = self.get_command_signature(command)
            embed.description = command.help or "No help found..."
            if command.aliases:
                aliases = ", ".join(map(lambda a: f"`{a}`", command.aliases))
                embed.add_field(name="Aliases", value=aliases)
            if (cooldown := command.cooldown) is not None:
                embed.add_field(name="Cooldown", value=f"`{cooldown.per}s`")

    async def send_bot_help(self, mapping):
        pages = get_bot_homepage(self.context)
        paginator = HelpPaginator(pages, ctx=self.context)
        paginator.add_categories(mapping)
        await paginator.start()

    async def send_cog_help(self, cog):
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        pages = await get_group_help_pages(self.context, cog, filtered)
        paginator = HelpPaginator(pages, ctx=self.context)
        await paginator.start()

    async def send_group_help(self, group):
        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        filtered = await self.filter_commands(subcommands, sort=True)
        pages = await get_group_help_pages(self.context, group, filtered)
        self.common_command_formatting(pages, group)
        paginator = HelpPaginator(pages, ctx=self.context)
        await paginator.start()

    async def send_command_help(self, command):
        embed = discord.Embed(color=self.context.bot.color(self.context.author.id))
        self.common_command_formatting(embed, command)
        await self.context.send(embed=embed)
