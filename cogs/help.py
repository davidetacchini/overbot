import discord
from discord.ext import commands


def chunks(entries, chunk):
    for x in range(0, len(entries), chunk):
        yield entries[x : x + chunk]


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def help_signature(self, command):
        parent = command.full_parent_name
        fmt = command.name if not parent else f"{parent} {command.name}"
        return f"{fmt} {command.signature}"

    def format_desc(self, command):
        return str(command.callback.__doc__).split(".")[0] + "."

    def embed_subcommands(self, embed, subcommands):
        for subcommand in subcommands:
            if subcommand.callback.__doc__:
                desc = self.format_desc(subcommand)
            else:
                desc = "No description set"
            if len(subcommand.aliases) > 0:
                desc = f"{desc}\nAliases: `{', '.join(subcommand.aliases)}`"
            embed.add_field(
                name=self.help_signature(subcommand),
                value=desc,
                inline=False,
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
        maxpages = len(all_commands)

        embed = discord.Embed(color=self.bot.color)
        embed.title = "Help"
        embed.set_footer(text=f"Page 1/{maxpages + 1}")
        embed.description = (
            f'Use "{ctx.prefix}help command" for more details on a command'
            f"\nOfficial website: {self.bot.config.website}"
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
            embed = discord.Embed(
                title=f"**{cog} Commands**",
                color=self.bot.color,
                timestamp=self.bot.timestamp,
            )
            embed.set_footer(
                text=f"Page {i + 1}/{maxpages + 1}",
            )
            for command in commands:
                subcommands = getattr(command, "commands", None)
                if command.callback.__doc__:
                    desc = self.format_desc(command)
                else:
                    desc = "No description set"
                if len(command.aliases) > 0:
                    desc = f"{desc}\nAliases: `{', '.join(command.aliases)}`"
                embed.add_field(
                    name=self.help_signature(command), value=desc, inline=False
                )
                if subcommands:
                    embed = self.embed_subcommands(embed, subcommands)
            pages.append(embed)
        return pages

    @commands.command()
    async def help(
        self, ctx, *, command: commands.clean_content(escape_markdown=True) = None
    ):
        """Get usage information for commands."""
        entered_command = command
        if command:
            command = self.bot.get_command(command.lower())
            if not command:
                return await ctx.send(f'No command called "{entered_command}" found.')
            sig = self.help_signature(command)
            subcommands = getattr(command, "commands", None)
            embed = discord.Embed(color=self.bot.color)
            embed.title = f"{ctx.prefix}{sig}"
            embed.description = getattr(command.callback, "__doc__")
            if len(command.aliases) > 0:
                aliases = ", ".join(command.aliases)
                embed.add_field(name="Aliases", value=aliases)
            if subcommands:
                embed = self.embed_subcommands(embed, subcommands)
            return await ctx.send(embed=embed)

        await self.bot.paginator.Paginator(extras=self.make_pages(ctx)).paginate(ctx)


def setup(bot):
    bot.add_cog(Help(bot))
