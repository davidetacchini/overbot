import json
import random
import secrets

import discord

from discord.ext import commands

from utils.i18n import _, locale
from classes.paginator import Choose


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
        _("""Play an Overwatch trivia game.""")
        question = self.get_question()
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

    async def get_member_stats(self, member):
        query = "SELECT * FROM trivia WHERE id = $1;"
        member_stats = await self.bot.pool.fetchrow(query, member.id)
        if not member_stats:
            raise commands.BadArgument(_("This member has no stats to show."))
        return member_stats

    def get_player_ratio(self, won, lost):
        if won >= 1 and lost == 0:
            return won
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
        return embed

    @trivia.command()
    @locale
    async def stats(self, ctx, member: discord.Member = None):
        _(
            """Shows trivia stats.

        `[member]` - The mention or the ID of a discord member of the current server.

        If no member is given then the stats returned will be yours.
        """
        )
        member = member or ctx.author
        stats = await self.get_member_stats(member)
        embed = self.embed_member_stats(member, stats)
        await ctx.send(embed=embed)

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
                ratio = self.get_player_ratio(player["won"], player["lost"])
                board.append(
                    _(
                        "{index}. **{player}** Played: {played} | Won: {won} | Lost: {lost} | Ratio: {ratio}"
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


def setup(bot):
    bot.add_cog(Trivia(bot))
