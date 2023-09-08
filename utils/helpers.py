from __future__ import annotations

from typing import TYPE_CHECKING

from discord.app_commands import Group, Choice

if TYPE_CHECKING:
    from discord import Interaction


async def hero_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    heroes = interaction.client.heroes
    return [
        Choice(name=value["name"], value=key)
        for key, value in heroes.items()
        if current.lower() in value["name"].lower() or current.lower() in key.lower()
    ][:25]


async def map_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    maps = interaction.client.maps
    return [
        Choice(name=value["name"], value=key)
        for key, value in maps.items()
        if current.lower() in value["name"].lower() or current.lower() in key.lower()
    ][:25]


async def gamemode_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    gamemodes = interaction.client.gamemodes
    return [
        Choice(name=value["name"], value=key)
        for key, value in gamemodes.items()
        if current.lower() in value["name"].lower() or current.lower() in key.lower()
    ]


async def module_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    modules = interaction.client.extensions
    return [
        Choice(name=module, value=module) for module in modules if current.lower() in module.lower()
    ]


async def profile_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    profile_cog = interaction.client.get_cog("profile")
    profiles = await profile_cog.get_profiles(interaction, interaction.user.id)
    return [
        Choice(name=profile.battletag, value=profile.id)
        for profile in profiles
        if current.lower() in profile.battletag.lower()
    ]


async def command_autocomplete(interaction: Interaction, current: str) -> list[Choice[str]]:
    commands = [c for c in interaction.client.tree.walk_commands()]
    return [
        Choice(name=command.qualified_name, value=command.qualified_name)
        for command in commands
        if current.lower() in command.qualified_name.lower() and not isinstance(command, Group)
    ][:25]
