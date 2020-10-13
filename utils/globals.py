import discord

from config import main_color


def embed_exception(exc):
    """Returns a custom embed for exceptions."""
    embed = discord.Embed(color=0xFF3232)
    embed.title = "An unknown error occured."
    embed.description = "Please report the following error to the developer by joning the support server at https://discord.gg/eZU69EV"
    embed.add_field(name="Error", value=exc, inline=False)
    return embed


def profile_info(ctx, platform, name):
    """Returns linked profile information."""
    embed = discord.Embed(color=main_color)
    embed.title = f"{ctx.author} Profile Information"
    embed.description = (
        "Here you can check the Overwatch profile linked to your Discord ID."
    )
    embed.add_field(name="Platform", value=platform)
    embed.add_field(name="Name", value=name)
    embed.add_field(
        name="Want to update it?",
        value=f"`{ctx.prefix}profile update <platform> <username>`",
        inline=False,
    )
    return embed


def group_signature(subcommand):
    """Returns groups commands signatures."""
    parent = subcommand.full_parent_name
    if len(subcommand.aliases) > 0:
        fmt = f"[{subcommand.name}|{'|'.join(subcommand.aliases)}]"
        if parent:
            fmt = f"{parent} {fmt}"
    else:
        fmt = subcommand.name if not parent else f"{parent} {subcommand.name}"
    return f"{fmt} {subcommand.signature}"


def group_embed(ctx, command):
    """Returns an embed for groups of commands."""
    subcommands = getattr(command, "commands", None)
    embed = discord.Embed(color=main_color)
    embed.title = f"{ctx.prefix}{command.name} [command]"
    embed.description = getattr(command.callback, "__doc__")
    for subcommand in subcommands:
        if subcommand.callback.__doc__:
            desc = subcommand.callback.__doc__
        else:
            desc = "No description set"
        embed.add_field(name=group_signature(subcommand), value=desc, inline=False)
    return embed
