from __future__ import annotations

import json
import random
import secrets

from typing import TYPE_CHECKING

import discord

from discord import app_commands
from discord.ext import commands

from classes.ui import SelectView, SelectAnswer
from classes.exceptions import NoChoice

if TYPE_CHECKING:
    from asyncpg import Record

    from bot import OverBot


class Trivia(commands.Cog):
    def __init__(self, bot: OverBot):
        self.bot = bot

    trivia = app_commands.Group(name="trivia", description="Play Overwatch trivia")

    def get_question(self) -> str:
        with open("assets/questions.json") as fp:
            questions = json.loads(fp.read())
        shuffled = random.sample(questions, len(questions))
        return secrets.choice(shuffled)

    async def get_answer(
        self,
        entries: list[str | discord.Embed],
        embed: discord.Embed,
        *,
        interaction: discord.Interaction,
        timeout: float,
    ) -> str:
        view = SelectView(author_id=interaction.user.id, timeout=timeout)
        select = SelectAnswer(placeholder="Select the correct answer...")
        view.add_item(select)

        embed.description = ""
        for index, entry in enumerate(entries, start=1):
            select.add_option(label=entry)
            embed.description = f"{embed.description}{index}. {entry}\n"

        view.message = await interaction.response.send_message(embed=embed, view=view)
        await view.wait()

        if (choice := select.values[0]) is not None:
            return choice
        raise NoChoice() from None

    async def get_result(self, interaction: discord.Interaction, question: dict) -> bool:
        entries = [question["correct_answer"]] + question["wrong_answers"]
        shuffled = random.sample(entries, len(entries))
        timeout = 45.0
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.title = question["question"]
        if question["image_url"]:
            embed.set_image(url=question["image_url"])
        embed.set_footer(text=f"You have 1 try and {timeout} seconds to respond.")
        answer = await self.get_answer(shuffled, embed, interaction=interaction, timeout=timeout)
        return answer == question["correct_answer"]

    async def update_member_games_started(self, member_id: int) -> None:
        query = """INSERT INTO trivia (id, started)
                   VALUES ($1, 1)
                   ON CONFLICT (id) DO
                   UPDATE SET started = trivia.started + 1;
                """
        await self.bot.pool.execute(query, member_id)

    async def update_member_stats(self, member_id: int, *, won: bool = True) -> None:
        if won:
            query = "UPDATE trivia SET won = won + 1 WHERE id = $1;"
        else:
            query = "UPDATE trivia SET lost = lost + 1 WHERE id = $1;"
        await self.bot.pool.execute(query, member_id)

    def embed_result(
        self, member: discord.Member, *, won: bool = True, correct_answer: str = None
    ) -> discord.Embed:
        embed = discord.Embed()
        embed.set_author(name=str(member), icon_url=member.display_avatar)
        if won:
            embed.color = discord.Color.green()
            embed.title = "Correct!"
            embed.set_footer(text="+1 win")
        else:
            embed.color = discord.Color.red()
            embed.title = "Wrong!"
            embed.set_footer(text="+1 loss")
            embed.add_field(name="Correct answer", value=correct_answer)
        return embed

    async def get_member_stats(self, member: discord.Member) -> Record:
        query = "SELECT * FROM trivia WHERE id = $1;"
        member_stats = await self.bot.pool.fetchrow(query, member.id)
        if not member_stats:
            raise commands.BadArgument("This member has no stats to show.")
        return member_stats

    def get_player_ratio(self, won: int, lost: int) -> float | int:
        if won >= 1 and lost == 0:
            return won
        try:
            return won / lost
        except ZeroDivisionError:
            return 0

    def embed_member_stats(self, member: discord.Member, stats: dict) -> discord.Embed:
        embed = discord.Embed(color=self.bot.color(member.id))
        embed.set_author(name=str(member), icon_url=member.display_avatar)
        unanswered = stats["started"] - (stats["won"] + stats["lost"])
        ratio = self.get_player_ratio(stats["won"], stats["lost"])
        embed.add_field(name="Total", value=stats["started"])
        embed.add_field(name="Won", value=stats["won"])
        embed.add_field(name="Lost", value=stats["lost"])
        embed.add_field(name="Ratio (W/L)", value="%.2f" % ratio)
        embed.add_field(name="Unanswered", value=unanswered)
        return embed

    @trivia.command()
    async def play(self, interaction: discord.Interaction):
        """Play an Overwatch trivia game."""
        question = self.get_question()
        await self.update_member_games_started(interaction.user.id)
        result = await self.get_result(interaction, question)
        if result:
            await self.update_member_stats(interaction.user.id)
            await interaction.followup.send(embed=self.embed_result(interaction.user))
        else:
            await self.update_member_stats(interaction.user.id, won=False)
            embed = self.embed_result(
                interaction.user, won=False, correct_answer=question["correct_answer"]
            )
            await interaction.followup.send(embed=embed)

    @trivia.command()
    async def stats(self, interaction: discord.Interaction, member: None | discord.Member = None):
        """Shows trivia stats.

        `[member]` - The mention or the ID of a discord member of the current server.

        If no member is given then the stats returned will be yours.
        """
        member = member or interaction.user
        stats = await self.get_member_stats(member)
        embed = self.embed_member_stats(member, stats)
        await interaction.response.send_message(embed=embed)

    @trivia.command()
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: (i.guild_id, i.user.id))
    async def best(self, interaction: discord.Interaction):
        """Shows top 10 trivia players.

        Based on games won.
        """
        query = """SELECT id, started, won, lost
                   FROM trivia
                   WHERE id <> $1
                   ORDER BY won DESC
                   LIMIT 10;
                """
        players = await self.bot.pool.fetch(query, self.bot.config.owner_id)
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.title = "Best Trivia Players"

        board = []
        for index, player in enumerate(players, start=1):
            cur_player = await self.bot.fetch_user(player["id"])
            ratio = self.get_player_ratio(player["won"], player["lost"])
            board.append(
                "{index}. **{player}** Played: {played} | Won: {won} | Lost: {lost} | Ratio: {ratio}".format(
                    index=index,
                    player=str(cur_player),
                    played=player["started"],
                    won=player["won"],
                    lost=player["lost"],
                    ratio=round(ratio, 2),
                )
            )
        embed.description = "\n".join(board)
        await interaction.response.send_message(embed=embed)


async def setup(bot: OverBot):
    await bot.add_cog(Trivia(bot))
