"""Configuration file for OverBot."""

"""Whether the version is realase or beta."""
DEBUG = True

"""The Bot token."""
token = "your_bot_token"
application_id = "your_application_id"
ignored_guilds = ()  # guilds (ids) to ignore when getting data from the database.

"""Database credentials."""
database = "postgresql://user:password@host:port/database"

# IGNORE (you don't actually need them to run the bot)
# NOTE: DEBUG must be set to True though

"""Webhook credentials."""
webhook = {
    "id": 0,
    "token": "",
}

"""The older commands count before renew the database."""
old_commands_count = 0

"""OverBot private API used to share bot information to its website."""
obapi = {
    "url": "",
    "token": "",
}

# ENDIGNORE

"""The owner's ID."""
owner_id = 285502621295312896

"""Prefix used if custom is not set."""
default_prefix = "-"

"""Default color used on most of the embeds"""
main_color = 0xFFA657

# IGNORE

"""OverBot's server ID."""
support_server_id = 550685823784321035

# ENDIGNORE

"""Guild ID for app commands testing. Also, the guild where cog Owner's related commands will be available."""
test_guild_id = None

"""Overwatch API url (unofficial)."""
base_url = "https://overfast-api.tekrop.fr"

"""GitHub links."""
github = {
    "profile": "https://github.com/davidetacchini/",
    "repo": "https://github.com/davidetacchini/overbot",
}

"""Overwatch endpoints."""
overwatch = {
    "status": "https://downdetector.com/status/overwatch-2/",
    "patch": "https://overwatch.blizzard.com/en-us/news/patch-notes/{}",
    "news": "https://overwatch.blizzard.com/en-us/news/",
    "account": "https://overwatch.blizzard.com/en-us/search/account-by-name",
}

"""Official website."""
website = "https://overbot.netlify.app"

"""Official support server invite."""
support = "https://discord.gg/8g3jnxv"

"""Invite link."""
invite = "https://discord.com/api/oauth2/authorize?client_id=547546531666984961&permissions=2281990160&scope=bot%20applications.commands"

"""Premium URL."""
premium = "https://overbot.netlify.app/premium"
