import json
import random
import asyncio
import secrets

import discord
from discord.ext import commands

from utils.i18n import _, locale
from utils.paginator import Choose


class MemberHasNoStats(Exception):
    """Exception raised when a member has no trivia stats to display."""

    def __init__(self, member):
        super().__init__(_(f"{member} hasn't played trivia yet."))


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
        timeout = 45.0
        footer = _(f"You have 1 try and {timeout} seconds to respond.")
        answer = await Choose(
            shuffled,
            timeout=timeout,
            title=question["question"],
            image=question["image_url"],
            footer=footer,
        ).start(ctx)
        return answer == question["correct_answer"]

    async def update_member_games_started(self, member_id):
        query = """INSERT INTO trivia(id, started)
                   VALUES($1, 1)
                   ON CONFLICT (id) DO
                   UPDATE SET started = trivia.started + 1;
                """
        await self.bot.pool.execute(query, member_id)

    async def update_member_games_won(self, member_id):
        query = "UPDATE trivia SET won = won + 1 WHERE id = $1;"
        await self.bot.pool.execute(query, member_id)

    async def update_member_games_lost(self, member_id):
        query = "UPDATE trivia SET lost = lost + 1 WHERE id = $1;"
        await self.bot.pool.execute(query, member_id)

    async def update_member_stats(self, member_id, *, won=True):
        if won:
            await self.update_member_games_won(member_id)
        else:
            await self.update_member_games_lost(member_id)

    def embed_result(self, member, *, won=True, correct_answer=None):
        embed = discord.Embed()
        embed.set_author(name=str(member), icon_url=member.avatar_url)
        if won:
            embed.color = discord.Color.green()
            embed.title = _("Correct!")
            embed.set_footer(text=_("+1 win"))
        else:
            embed.color = discord.Color.red()
            embed.title = _("Wrong!")
            embed.set_footer(text=_("+1 loss"))
            embed.add_field(name=_("Correct answer"), value=correct_answer)
        return embed

    @commands.group(invoke_without_command=True)
    @locale
    async def trivia(self, ctx):
        _("""Displays a list with all trivia's subcommands.""")
        embed = self.bot.get_subcommands(ctx, ctx.command)
        await ctx.send(embed=embed)

    @trivia.command()
    @locale
    async def play(self, ctx):
        _("""Play Overwatch trivia.""")
        try:
            question = self.get_question()
        except Exception as e:
            await ctx.send(embed=self.bot.embed_exception(e))

        await self.update_member_games_started(ctx.author.id)

        result = await self.get_result(ctx, question)
        if result:
            await self.update_member_stats(ctx.author.id)
            await ctx.send(embed=self.embed_result(ctx.author))
        else:
            await self.update_member_stats(ctx.author.id, won=False)
            embed = self.embed_result(
                ctx.author, won=False, correct_answer=question["correct_answer"]
            )
            await ctx.send(embed=embed)

    async def get_member_trivia_stats(self, member):
        query = "SELECT * FROM trivia WHERE id = $1;"
        member_stats = await self.bot.pool.fetchrow(query, member.id)
        if not member_stats:
            raise MemberHasNoStats(member)
        return member_stats

    def get_player_ratio(self, won, lost):
        if won >= 1 and lost == 0:
            return won
        else:
            try:
                return won / lost
            except ZeroDivisionError:
                return 0

    def embed_member_stats(self, member, stats):
        embed = discord.Embed(color=self.bot.color(member.id))
        embed.set_author(name=str(member), icon_url=member.avatar_url)
        unanswered = stats["started"] - (stats["won"] + stats["lost"])
        ratio = self.get_player_ratio(stats["won"], stats["lost"])
        embed.add_field(name=_("Total"), value=stats["started"])
        embed.add_field(name=_("Won"), value=stats["won"])
        embed.add_field(name=_("Lost"), value=stats["lost"])
        embed.add_field(name=_("Ratio (W/L)"), value="%.2f" % ratio)
        embed.add_field(name=_("Unanswered"), value=unanswered)
        embed.add_field(name=_("Contributions"), value=stats["contribs"])
        return embed

    @trivia.command(aliases=["statistics"])
    @locale
    async def stats(self, ctx, member: discord.Member = None):
        _(
            """Shows trivia stats.

        `[member]` - The mention or the ID of a discord member of the current server.

        If no member is given then the stats returned will be yours.
        """
        )
        member = member or ctx.author
        try:
            stats = await self.get_member_trivia_stats(member)
        except MemberHasNoStats as e:
            return await ctx.send(e)

        try:
            embed = self.embed_member_stats(member, stats)
        except Exception as e:
            await ctx.send(e)
        else:
            await ctx.send(embed=embed)

    def get_placement(self, place):
        placements = {
            1: ":first_place:",
            2: ":second_place:",
            3: ":third_place:",
            4: ":four:",
            5: ":five:",
            6: ":six:",
            7: ":seven:",
            8: ":eight:",
            9: ":nine:",
            10: ":keycap_ten:",
        }
        return placements.get(place)

    @trivia.command(aliases=["top"])
    @commands.cooldown(1, 60.0, commands.BucketType.member)
    @locale
    async def best(self, ctx):
        _(
            """Shows the best OverBot's trivia players.

        It is based on games won.

        This command can be used once per minute.
        """
        )
        async with ctx.typing():
            query = """SELECT id, started, won, lost
                       FROM trivia
                       WHERE id <> $1
                       ORDER BY won DESC
                       LIMIT 10;
                    """
            players = await self.bot.pool.fetch(query, self.bot.config.owner_id)
            embed = discord.Embed(color=self.bot.color(ctx.author.id))
            embed.title = _("Best Trivia Players")

            board = []
            for index, player in enumerate(players, start=1):
                cur_player = await self.bot.fetch_user(player["id"])
                placement = self.get_placement(index)
                ratio = self.get_player_ratio(player["won"], player["lost"])
                board.append(
                    _(
                        "{placement} **{player}** Played: {played} | Won: {won} | Lost: {lost} | Ratio: {ratio}"
                    ).format(
                        placement=placement,
                        player=str(cur_player),
                        played=player["started"],
                        won=player["won"],
                        lost=player["lost"],
                        ratio=round(ratio, 2),
                    )
                )
            embed.description = "\n".join(board)
            await ctx.send(embed=embed)

    def get_submit_message(self):
        return _(
            "Copy everything inside the code block below and hit the green checkmark.\n"
            '```"question": "REPLACE",\n'
            '"image_url": "REAPLCE",\n'
            '"correct_answer": "REPLACE",\n'
            '"wrong_answers": [min 1 max 4]```'
        )

    async def update_member_contribs_stats(self, member_id):
        query = """INSERT INTO trivia(id, contribs)
                   VALUES($1, 1)
                   ON CONFLICT (id) DO
                   UPDATE SET contribs = trivia.contribs + 1;
                """
        await self.bot.pool.execute(query, member_id)

    def format_content(self, content):
        if content.startswith("```") and content.endswith("```"):
            return content
        return "```json\n" + content + "```"

    @trivia.command(aliases=["contrib"])
    @commands.cooldown(1, 3600, commands.BucketType.member)
    @locale
    async def submit(self, ctx):
        _(
            """Submit a new question to be added to trivia.

        You can submit a request once an hour.
        """
        )
        if not await ctx.prompt(self.get_submit_message()):
            return

        await ctx.send(
            _(
                "Paste the code you copied before, replace everything and hit enter. You have 60 seconds."
            )
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
            await ctx.send(_("You took too long to submit the request."))
        else:
            channel = self.bot.get_channel(self.bot.config.trivia_channel)
            if not channel:
                return
            content = self.format_content(message.content)
            await channel.send(content)
            await self.update_member_contribs_stats(ctx.author.id)
            await ctx.send(
                _(
                    "{author}, your request has been successfully sent. Thanks for the contribution!"
                ).format(author=str(ctx.author))
            )


def setup(bot):
    bot.add_cog(Trivia(bot))
