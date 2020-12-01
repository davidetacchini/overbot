import json
import random
import secrets

import discord
from asyncpg import UniqueViolationError
from discord.ext import commands

import asyncio
from utils.paginator import Choose


class MemberHasNoStats(Exception):
    """Exception raised when a member has no trivia statistics to display."""

    def __init__(self, member):
        super().__init__(f"{member} hasn't played trivia yet.")


class Trivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_question(self):
        with open("assets/questions.json") as fp:
            questions = json.loads(fp.read())
        shuffled = random.sample(questions, len(questions))
        return secrets.choice(shuffled)

    async def get_result(self, ctx, question):
        entries = [question["correct_answer"]] + question["wrong_answers"]
        shuffled = random.sample(entries, len(entries))
        footer = "You have 1 try and 30 seconds to respond."
        answer = await Choose(
            shuffled,
            title=question["question"],
            footer=footer,
            image=question["image_url"],
        ).paginate(ctx)
        return answer == question["correct_answer"]

    async def update_member_games_started(self, member_id):
        try:
            await self.bot.pool.execute(
                "INSERT INTO trivia (id, started) VALUES ($1, $2)", member_id, 1
            )
        except UniqueViolationError:
            await self.bot.pool.execute(
                "UPDATE trivia SET started=started+1 WHERE id=$1", member_id
            )

    async def update_member_games_won(self, member_id):
        await self.bot.pool.execute(
            "UPDATE trivia SET won=won+1 WHERE id=$1", member_id
        )

    async def update_member_games_lost(self, member_id):
        await self.bot.pool.execute(
            "UPDATE trivia SET lost=lost+1 WHERE id=$1", member_id
        )

    async def update_member_stats(self, member_id, *, won=True):
        if won:
            await self.update_member_games_won(member_id)
        else:
            await self.update_member_games_lost(member_id)

    @commands.group()
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    async def trivia(self, ctx):
        try:
            question = self.get_question()
        except Exception as exc:
            await ctx.send(embed=self.bot.embed_exception(exc))
        await self.update_member_games_started(ctx.author.id)
        result = await self.get_result(ctx, question)
        if result:
            await self.update_member_stats(ctx.author.id)
            await ctx.send("Correct!")
        else:
            await self.update_member_stats(ctx.author.id, won=False)
            await ctx.send(f"Wrong! Correct answer is: `{question['correct_answer']}`")

    async def get_member_trivia_stats(self, member):
        member_stats = await self.bot.pool.fetchrow(
            "SELECT * FROM trivia WHERE id=$1", member.id
        )
        if not member_stats:
            raise MemberHasNoStats(member)
        return member_stats

    def embed_member_stats(self, member, stats):
        embed = discord.Embed(color=member.color)
        embed.set_author(name=str(member), icon_url=member.avatar_url)
        unanswered = stats["started"] - (stats["won"] + stats["lost"])
        try:
            ratio = stats["won"] / stats["lost"]
        except ZeroDivisionError:
            ratio = 0
        embed.add_field(name="Total", value=stats["started"])
        embed.add_field(name="Won", value=stats["won"])
        embed.add_field(name="Lost", value=stats["lost"])
        embed.add_field(name="Ratio (W/L)", value="%.2f" % ratio)
        embed.add_field(name="Unanswered", value=unanswered)
        embed.add_field(name="Contributions", value=stats["contribs"])
        return embed

    @trivia.command(aliases=["stats"])
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    async def statistics(self, ctx, member: discord.Member = None):
        """Shows trivia statistics.

        `[member]` - The mention or the ID of a discord member of the current server.

        If no member is given then the stats returned will be yours.
        """
        member = member or ctx.author
        try:
            stats = await self.get_member_trivia_stats(member)
        except MemberHasNoStats as exc:
            await ctx.send(exc)
        else:
            try:
                embed = self.embed_member_stats(member, stats)
            except Exception as exc:
                await ctx.send(exc)
            else:
                await ctx.send(embed=embed)

    def get_placement(self, place):
        placements = {1: ":first_place:", 2: ":second_place:", 3: ":third_place:"}
        return placements.get(place)

    @trivia.command(aliases=["top"])
    @commands.cooldown(1, 60.0, commands.BucketType.member)
    async def best(self, ctx):
        """Displays a leaderboard of the 10 trivia players.

        It is based on games won.

        This command can be used once a minute.
        """
        async with ctx.typing():
            players = await self.bot.pool.fetch(
                "SELECT id, started, won, lost FROM trivia WHERE "
                "id <> 285502621295312896 ORDER BY won DESC LIMIT 10"
            )
            embed = discord.Embed()
            embed.title = "Best Trivia Players"

            board = []
            for i, player in enumerate(players, start=1):
                p = await self.bot.fetch_user(player["id"])
                placement = self.get_placement(i)
                try:
                    ratio = player["won"] / player["lost"]
                except ZeroDivisionError:
                    ratio = 0
                board.append(
                    f'{placement} **{str(p)}** Played: {player["started"]}'
                    f'| Won: {player["won"]} | Lost: {player["lost"]} | Ratio: {ratio:.2f}'
                )
            embed.description = "\n".join(board)
            await ctx.send(embed=embed)

    def get_submit_message(self):
        return (
            "Copy everything inside the code block below and hit enter."
            "NOTE: If your question is a true/false one, you should know what to do.\n"
            '```"question": "REPLACE",\n"image_url": "REAPLCE",\n"correct_answer": "REPLACE",\n'
            '"wrong_answers": [min 1 max 4]```'
        )

    async def update_member_contribs_stats(self, member_id):
        try:
            await self.bot.pool.execute(
                "INSERT INTO trivia (id, contribs) VALUES ($1, $2)", member_id, 1
            )
        except UniqueViolationError:
            await self.bot.pool.execute(
                "UPDATE trivia SET contribs=contribs+1 WHERE id=$1", member_id
            )

    def format_content(self, content):
        """Automatically removes code blocks from the code."""
        if content.startswith("```") and content.endswith("```"):
            return content
        return "```json\n" + content + "```"

    @trivia.command(aliases=["contrib"])
    @commands.cooldown(1, 3600, commands.BucketType.member)
    async def submit(self, ctx):
        """Submit a new question to be added to trivia.

        You can submit a request once an hour.
        """
        if not await ctx.prompt(self.get_submit_message()):
            return

        await ctx.send(
            "Paste the code you copied before, replace everything and hit enter. You have 60 seconds."
        )

        def check(m):
            if m.author.id != ctx.author.id:
                return False
            if m.channel.id != ctx.channel.id:
                return False
            return True

        try:
            message = await self.bot.wait_for("message", check=check, timeout=60.0)
        except asyncio.TimeoutError:
            await ctx.send("You took too long to submit the request.")
        else:
            try:
                channel = self.bot.config.trivia_channel
                content = self.format_content(message.content)
                await self.bot.http.send_message(channel, content)
            except Exception as exc:
                await ctx.send(embed=self.bot.embed_exception(exc))
            else:
                await self.update_member_contribs_stats(ctx.author.id)
                await ctx.send(
                    f"{str(ctx.author)}, your request has been successfully sent. Thanks for the contribution!"
                )


def setup(bot):
    bot.add_cog(Trivia(bot))
