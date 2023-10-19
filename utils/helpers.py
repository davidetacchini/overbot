from __future__ import annotations

from typing import TYPE_CHECKING

from discord.app_commands import Choice, Group

if TYPE_CHECKING:
    from discord import Interaction

    from bot import OverBot
    from cogs.profile import ProfileCog


async def hero_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    bot: OverBot = getattr(interaction, "client")
    return [
        Choice(name=value["name"], value=key)
        for key, value in bot.heroes.items()
        if current.lower() in value["name"].lower() or current.lower() in key.lower()
    ][:25]


async def map_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    bot: OverBot = getattr(interaction, "client")
    return [
        Choice(name=value["name"], value=key)
        for key, value in bot.maps.items()
        if current.lower() in value["name"].lower() or current.lower() in key.lower()
    ][:25]


async def gamemode_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    bot: OverBot = getattr(interaction, "client")
    return [
        Choice(name=value["name"], value=key)
        for key, value in bot.gamemodes.items()
        if current.lower() in value["name"].lower() or current.lower() in key.lower()
    ]


async def module_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    bot: OverBot = getattr(interaction, "client")
    return [
        Choice(name=module, value=module)
        for module in bot.extensions
        if current.lower() in module.lower()
    ]


async def profile_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    profile_cog: ProfileCog = interaction.client.get_cog("profile")  # type: ignore
    profiles = await profile_cog.get_profiles(interaction, interaction.user.id)
    return [
        Choice(name=profile.battletag, value=profile.id)  # type: ignore
        for profile in profiles
        if current.lower() in profile.battletag.lower()  # type: ignore
    ]


async def command_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    bot: OverBot = getattr(interaction, "client")
    commands = [c for c in bot.tree.walk_commands()]
    return [
        Choice(name=command.qualified_name, value=command.qualified_name)
        for command in commands
        if current.lower() in command.qualified_name.lower() and not isinstance(command, Group)
    ][:25]
