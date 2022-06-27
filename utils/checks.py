from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from discord import app_commands

if TYPE_CHECKING:
    from asyncpg import Record


class ProfileNotLinked(app_commands.CheckFailure):

    pass


class ProfileLimitReached(app_commands.CheckFailure):
    def __init__(self, limit):
        self.limit = limit


class MemberNotPremium(app_commands.CheckFailure):

    pass


class NotOwner(app_commands.CheckFailure):

    pass


async def get_profiles(interaction: discord.Interaction) -> list[Record]:
    query = """SELECT platform, username
               FROM profile
               INNER JOIN member
                       ON member.id = profile.member_id
               WHERE member.id = $1;
            """
    return await interaction.client.pool.fetch(query, interaction.user.id)


def has_profile():
    """Check for a user to have linked atleast a profile."""

    async def predicate(interaction: discord.Interaction):
        if await get_profiles(interaction):
            return True
        raise ProfileNotLinked()

    return app_commands.check(predicate)


def can_add_profile():
    """Check for a user to have no profiles linked."""

    async def predicate(interaction: discord.Interaction):
        profiles = await get_profiles(interaction)
        limit = interaction.client.get_profiles_limit(interaction, interaction.user.id)

        if len(profiles) >= limit:
            raise ProfileLimitReached(limit)
        return True

    return app_commands.check(predicate)


def is_premium():
    """Check for a user/server to be premium."""

    def predicate(interaction: discord.Interaction):
        member_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild is not None else 0
        to_check = (member_id, guild_id)

        if all(x not in interaction.client.premiums for x in to_check):
            raise MemberNotPremium()
        return True

    return app_commands.check(predicate)


def is_owner():
    def predicate(interaction: discord.Interaction):
        if interaction.user.id == interaction.client.owner.id:
            return True
        raise NotOwner()

    return app_commands.check(predicate)
