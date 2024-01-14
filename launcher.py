# Inspired by https://github.com/Rapptz/RoboDanny, customized for OverBot
from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import re
import sys
import traceback
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TypedDict

import asyncpg
import click
import discord

import config
from bot import OverBot

log = logging.getLogger()

if sys.platform == "linux" or sys.platform == "darwin":
    import uvloop

    uvloop.install()


class Revisions(TypedDict):
    # The version key represents the current activated version
    # So v1 means v1 is active and the next revision should be v2
    # In order for this to work the number has to be monotonically increasing
    # and have no gaps
    version: int
    database_uri: str


REVISION_FILE = re.compile(r"(?P<kind>V|U)(?P<version>[0-9]+)_Migration.sql")


class Revision:
    __slots__ = ("kind", "version", "description", "file")

    def __init__(self, *, kind: str, version: int, description: str, file: Path) -> None:
        self.kind: str = kind
        self.version: int = version
        self.description: str = description
        self.file: Path = file

    @classmethod
    def from_match(cls, match: re.Match[str], file: Path):
        return cls(
            kind=match.group("kind"),
            version=int(match.group("version")),
            description="Migration",
            file=file,
        )


class Migrations:
    def __init__(self, *, filename: str = "migrations/revisions.json"):
        self.filename: str = filename
        self.root: Path = Path(filename).parent
        self.revisions: dict[int, Revision] = self.get_revisions()
        self.load()

    def ensure_path(self) -> None:
        self.root.mkdir(exist_ok=True)

    def load_metadata(self) -> Revisions:
        try:
            with open(self.filename, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except FileNotFoundError:
            return {
                "version": 0,
                "database_uri": discord.utils.MISSING,
            }

    def get_revisions(self) -> dict[int, Revision]:
        result: dict[int, Revision] = {}
        for file in self.root.glob("*.sql"):
            match = REVISION_FILE.match(file.name)
            if match is not None:
                rev = Revision.from_match(match, file)
                result[rev.version] = rev

        return result

    def dump(self) -> Revisions:
        return {
            "version": self.version,
            "database_uri": self.database_uri,
        }

    def load(self) -> None:
        self.ensure_path()
        data = self.load_metadata()
        self.version: int = data["version"]
        self.database_uri: str = data["database_uri"]

    def save(self):
        temp = f"{self.filename}.{uuid.uuid4()}.tmp"
        with open(temp, "w", encoding="utf-8") as tmp:
            json.dump(self.dump(), tmp)

        # atomically move the file
        os.replace(temp, self.filename)

    def is_next_revision_taken(self) -> bool:
        return self.version + 1 in self.revisions

    @property
    def ordered_revisions(self) -> list[Revision]:
        return sorted(self.revisions.values(), key=lambda r: r.version)

    def create_revision(self, reason: str, *, kind: str = "V") -> Revision:
        filename = f"{kind}{self.version + 1}_Migration.sql"
        path = self.root / filename

        stub = (
            f"-- Revises: V{self.version}\n"
            f"-- Creation Date: {datetime.datetime.utcnow()} UTC\n"
            f"-- Reason: {reason}\n\n"
        )

        with open(path, "w", encoding="utf-8", newline="\n") as fp:
            fp.write(stub)

        self.save()
        return Revision(kind=kind, description=reason, version=self.version + 1, file=path)

    async def upgrade(self, connection: asyncpg.Connection) -> int:
        ordered = self.ordered_revisions
        successes = 0
        async with connection.transaction():
            for revision in ordered:
                if revision.version > self.version:
                    sql = revision.file.read_text("utf-8")
                    await connection.execute(sql)
                    successes += 1

        self.version += successes
        self.save()
        return successes

    def display(self) -> None:
        ordered = self.ordered_revisions
        for revision in ordered:
            if revision.version > self.version:
                sql = revision.file.read_text("utf-8")
                click.echo(sql)


def setup_logging() -> None:
    discord.utils.setup_logging()

    if not Path("logs").exists():
        Path("logs").mkdir(parents=True, exist_ok=True)

    max_bytes = 32 * 1024 * 1024  # 32MiB
    handler = RotatingFileHandler(
        filename="logs/overbot.log", mode="w", maxBytes=max_bytes, backupCount=5, encoding="utf-8"
    )
    dt_format = "%d-%m-%Y %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_format, style="{"
    )
    handler.setFormatter(formatter)
    log.addHandler(handler)


async def run_bot() -> None:
    intents = discord.Intents(
        guilds=True,
        members=True,
        messages=True,
        reactions=True,
    )

    async with OverBot(
        activity=discord.Game(name="Starting..."),
        status=discord.Status.dnd,
        allowed_mentions=discord.AllowedMentions.none(),
        application_id=config.application_id,
        intents=intents,
        chunk_guilds_at_startup=False,
    ) as bot:
        bot.pool = await asyncpg.create_pool(
            config.database, min_size=20, max_size=20, command_timeout=120.0
        )  # type: ignore
        await bot.start()


@click.group(invoke_without_command=True, options_metavar="[options]")
@click.pass_context
def main(ctx):
    """Launches the bot"""
    if ctx.invoked_subcommand is None:
        setup_logging()
        asyncio.run(run_bot())


@main.group(short_help="Database commands", options_metavar="[options]")
def db():
    pass


async def ensure_uri_can_run() -> bool:
    connection: asyncpg.Connection = await asyncpg.connect(config.database)
    await connection.close()
    return True


@db.command()
def init():
    """Initializes the database and runs all the current migrations"""
    asyncio.run(ensure_uri_can_run())

    migrations = Migrations()
    migrations.database_uri = config.database

    try:
        applied = asyncio.run(run_upgrade(migrations))
    except Exception:
        traceback.print_exc()
        click.secho("failed to initialize and apply migrations due to error", fg="red")
    else:
        click.secho(f"Successfully initialized and applied {applied} revisions(s)", fg="green")


@db.command()
@click.option("--reason", "-r", help="The reason for this revision.", required=True)
def migrate(reason):
    """Creates a new revision for you to edit"""
    migrations = Migrations()
    if migrations.is_next_revision_taken():
        click.echo("an unapplied migration already exists for the next version, exiting")
        click.secho("hint: apply pending migrations with the `upgrade` command", bold=True)
        return

    revision = migrations.create_revision(reason)
    click.echo(f"Created revision V{revision.version!r}")


async def run_upgrade(migrations: Migrations) -> int:
    connection: asyncpg.Connection = await asyncpg.connect(migrations.database_uri)
    return await migrations.upgrade(connection)


@db.command()
@click.option("--sql", help="Print the SQL instead of executing it", is_flag=True)
def upgrade(sql):
    """Upgrades the database at the given revision (if any)"""
    migrations = Migrations()

    if sql:
        migrations.display()
        return

    try:
        applied = asyncio.run(run_upgrade(migrations))
    except Exception:
        traceback.print_exc()
        click.secho("failed to apply migrations due to error", fg="red")
    else:
        click.secho(f"Applied {applied} revisions(s)", fg="green")


@db.command()
def current():
    """Shows the current active revision version"""
    migrations = Migrations()
    click.echo(f"Version {migrations.version}")


@db.command()
@click.option("--reverse", help="Print in reverse order (oldest first).", is_flag=True)
def history(reverse):
    """Displays the revision history"""
    migrations = Migrations()
    # Revisions is oldest first already
    revs = reversed(migrations.ordered_revisions) if not reverse else migrations.ordered_revisions
    for rev in revs:
        as_yellow = click.style(f"V{rev.version:>03}", fg="yellow")
        click.echo(f'{as_yellow} {rev.description.replace("_", " ")}')


if __name__ == "__main__":
    main()
