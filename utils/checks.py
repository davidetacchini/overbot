from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from discord import app_commands

if TYPE_CHECKING:
    from asyncpg import Record

from classes.exceptions import NotOwner, NotPremium, ProfileNotLinked, ProfileLimitReached


async def get_profiles(interaction: discord.Interaction, member_id: int) -> list[Record]:
    query = """SELECT platform, username
               FROM profile
               INNER JOIN member
                       ON member.id = profile.member_id
               WHERE member.id = $1;
            """
    return await interaction.client.pool.fetch(query, member_id)


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
    """Check for a user to have no profiles linked."""

    async def predicate(interaction: discord.Interaction) -> bool:
        profiles = await get_profiles(interaction, interaction.user.id)
        limit = interaction.client.get_profiles_limit(interaction, interaction.user.id)

        if len(profiles) <= limit:
            return True
        raise ProfileLimitReached(limit)

    return app_commands.check(predicate)


def is_premium():
    """Check for a user/server to be premium."""

    def predicate(interaction: discord.Interaction) -> bool:
        user_id = interaction.user.id
        guild_id = interaction.guild_id or 0

        if interaction.client.is_it_premium(user_id, guild_id):
            return True
        raise NotPremium()

    return app_commands.check(predicate)


def is_owner():
    def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id == interaction.client.owner.id:
            return True
        raise NotOwner()

    return app_commands.check(predicate)


def subcommand_guild_only():
    # Due to a Discord limitation the @app_commands.guild_only
    # decorator does not work for subcommands.
    def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is not None:
            return True
        raise app_commands.NoPrivateMessage()

    return app_commands.check(predicate)
