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
        if len(command.aliases) > 0:
            fmt = f"[{command.name}|{'|'.join(command.aliases)}]"
            if parent:
                fmt = f"{parent} {fmt}"
        else:
            fmt = command.name if not parent else f"{parent} {command.name}"
        return f"{fmt} {command.signature}"

    def embed_subcommands(self, embed, subcommands):
        for subcommand in subcommands:
            if subcommand.callback.__doc__:
                desc = subcommand.callback.__doc__
            else:
                desc = "No description set"
            embed.add_field(
                name=self.help_signature(subcommand),
                value=desc,
                inline=False,
            )
        return embed

    def make_pages(self, ctx):
        all_commands = {}
        for cog, instance in self.bot.cogs.items():
            # avoid showing commands for this cog/s
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

        embed = discord.Embed(
            color=self.bot.color,
            timestamp=self.bot.timestamp,
        )
        embed.title = f"{self.bot.user.name} Help"
        embed.description = f"Use the arrows in order to move through the pages\nOfficial website: {self.bot.config.website}"
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.add_field(
            name="Command details",
            value=f"Run `{ctx.prefix}help <command_name>` for details on a command",
        )
        embed.add_field(
            name="Note",
            value="You **must not** use the brackets in the argument",
            inline=False,
        )
        embed.add_field(
            name="Need more help?",
            value=f"Join the official support server at {self.bot.config.support}",
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
                text=f"Page {i}/{maxpages}",
            )
            for command in commands:
                subcommands = getattr(command, "commands", None)
                if command.callback.__doc__:
                    desc = command.callback.__doc__
                else:
                    desc = "No description set"
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
        if command:
            command = self.bot.get_command(command.lower())
            if not command:
                return await ctx.send("Sorry, typed command doesn't exist.")
            sig = self.help_signature(command)
            subcommands = getattr(command, "commands", None)
            embed = discord.Embed(color=self.bot.color)
            embed.title = f"{ctx.prefix}{sig}"
            embed.description = getattr(command.callback, "__doc__")
            if subcommands:
                embed = self.embed_subcommands(embed, subcommands)
            return await ctx.send(embed=embed)

        await self.bot.paginator.Paginator(extras=self.make_pages(ctx)).paginate(ctx)


def setup(bot):
    bot.add_cog(Help(bot))
