from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands

import config

if TYPE_CHECKING:
    from asyncpg import Record

from classes.exceptions import (
    NotOwner,
    NotPremium,
    NotSupportServer,
    ProfileLimitReached,
    ProfileNotLinked,
)


async def get_profiles(interaction: discord.Interaction, member_id: int) -> list[Record]:
    query = """SELECT battletag
               FROM profile
               INNER JOIN member
                       ON member.id = profile.member_id
               WHERE member.id = $1;
            """
    return await interaction.client.pool.fetch(query, member_id)  # type: ignore


def has_profile():
    """Check for a user to have linked at least a profile."""

    def get_target_id(interaction) -> int:
        try:
            return interaction.namespace.member.id
        except AttributeError:
            return interaction.user.id

    async def predicate(interaction: discord.Interaction) -> bool:
        target_id = get_target_id(interaction)
        if await get_profiles(interaction, target_id):
            return True
        raise ProfileNotLinked(is_author=target_id == interaction.user.id)

    return app_commands.check(predicate)


def can_add_profile():
    """Check for a user to have available profile slots."""

    async def predicate(interaction: discord.Interaction) -> bool:
        profiles = await get_profiles(interaction, interaction.user.id)
        profile_cog = interaction.client.get_cog("profile")  # type: ignore
        limit = profile_cog.get_profiles_limit(interaction, interaction.user.id)

        if len(profiles) <= limit:
            return True
        raise ProfileLimitReached(limit)

    return app_commands.check(predicate)


def is_premium():
    """Check for a user/server to be premium."""

    def predicate(interaction: discord.Interaction) -> bool:
        user_id = interaction.user.id
        guild_id = interaction.guild_id or 0

        if interaction.client.is_it_premium(user_id, guild_id):  # type: ignore
            return True
        raise NotPremium()

    return app_commands.check(predicate)


def is_owner():
    def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id == interaction.client.owner.id:  # type: ignore
            return True
        raise NotOwner()

    return app_commands.check(predicate)


def is_support_server():
    def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild_id == config.support_server_id:
            return True
        raise NotSupportServer()

    return app_commands.check(predicate)
