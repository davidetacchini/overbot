import discord
from discord.ext import commands


def chunks(entries, size):
    for x in range(0, len(entries), size):
        yield entries[x : x + size]


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def format_aliases(self, aliases):
        return [f"`{alias}`" for alias in aliases]

    def format_desc(self, command):
        return str(command.callback.__doc__).split(".")[0] + "."

    def command_signature(self, command):
        parent = command.full_parent_name
        fmt = command.name if not parent else f"{parent} {command.name}"
        return f"{fmt} {command.signature}"

    def command_embed(self, embed, subcommands):
        for subcommand in subcommands:
            if subcommand.callback.__doc__:
                desc = self.format_desc(subcommand)
            else:
                desc = "No description set"
            if len(subcommand.aliases) > 0:
                aliases = self.format_aliases(subcommand.aliases)
                desc = f"{desc}\nAliases: {', '.join(aliases)}"
            embed.add_field(
                name=self.command_signature(subcommand), value=desc, inline=False
            )
        return embed

    def make_pages(self, ctx):
        all_commands = {}
        for cog, instance in self.bot.cogs.items():
            if cog in ["Owner", "Tasks"]:
                continue
            commands = list(chunks(list(instance.get_commands()), 10))
            if len(commands) == 1:
                all_commands[cog] = commands[0]
            else:
                for i, j in enumerate(commands, start=1):
                    all_commands[f"{cog} ({i}/{len(commands)})"] = j

        pages = []
        max_pages = len(all_commands)

        embed = discord.Embed(color=self.bot.color)
        embed.title = "Help"
        embed.set_footer(text=f"Page 1/{max_pages + 1}")
        embed.description = (
            f"Use `{ctx.prefix}help [command]` for more details on a command\n"
            "Replace [command] with an existing command.\n"
            f"Official website: {self.bot.config.website}"
        )
        embed.add_field(
            name="Note",
            value="You **must not** use the brackets in the argument",
            inline=False,
        )
        embed.add_field(
            name="Need more help?",
            value=f"Join the official bot support server: {self.bot.config.support}",
            inline=False,
        )

        pages.append(embed)
        for i, (cog, commands) in enumerate(all_commands.items(), start=1):
            embed = discord.Embed(color=self.bot.color)
            embed.title = f"**{cog} Commands**"
            embed.timestamp = (self.bot.timestamp,)
            embed.set_footer(
                text=f"Page {i + 1}/{max_pages + 1}",
            )
            for command in commands:
                subcommands = getattr(command, "commands", None)
                if command.callback.__doc__:
                    desc = self.format_desc(command)
                else:
                    desc = "No description set"
                if len(command.aliases) > 0:
                    aliases = self.format_aliases(command.aliases)
                    desc = f"{desc}\nAliases: {', '.join(aliases)}"
                embed.add_field(
                    name=self.command_signature(command), value=desc, inline=False
                )
                if subcommands:
                    embed = self.command_embed(embed, subcommands)
            pages.append(embed)
        return pages

    @commands.command()
    async def help(
        self, ctx, *, command: commands.clean_content(escape_markdown=True) = None
    ):
        """Shows help about the bot or commands."""
        entered_command = command
        if command:
            command = self.bot.get_command(command.lower())
            if not command:
                return await ctx.send(f'No command called "{entered_command}" found.')
            sig = self.command_signature(command)
            subcommands = getattr(command, "commands", None)
            embed = discord.Embed(color=self.bot.color)
            embed.title = f"{ctx.prefix}{sig}"
            embed.description = getattr(command.callback, "__doc__")
            if len(command.aliases) > 0:
                aliases = ", ".join(self.format_aliases(command.aliases))
                embed.add_field(name="Aliases", value=aliases)
            if subcommands:
                embed = self.command_embed(embed, subcommands)
            return await ctx.send(embed=embed)

        await self.bot.paginator.Paginator(pages=self.make_pages(ctx)).paginate(ctx)


def setup(bot):
    bot.add_cog(Help(bot))
