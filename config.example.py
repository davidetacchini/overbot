"""Whether the version is realase or beta."""
DEBUG = True

"""The Bot token."""
token = "your_bot_token"
application_id = "your_application_id"
ignored_guilds = ()  # guilds to ignore when getting data from the database.

"""Database credentials."""
database = {
    "user": "davide",
    "password": "your_password",
    "database": "overbot",
    "host": "localhost",
}

# IGNORE (you don't actually need them to run the bot)
# NOTE: DEBUG must be set to True though

"""DonateBot API authorization."""
dbot = {
    "new": "endpoint for new donations",
    "mark": "endpoint to mark donation as processed",
    "api_key": "personal api key",
    "product_ids": {
        "member": "member product ID",
        "server": "server product ID",
    },
}

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

"""Premium consts."""
PREMIUM_PROFILES_LIMIT = 25

"""Base consts."""
DEFAULT_PROFILES_LIMIT = 5

"""The owner's ID."""
owner_id = 285502621295312896

"""Prefix used if custom is not set."""
default_prefix = "-"

"""Default color used on most of the embeds"""
main_color = 0xFFA657

# IGNORE

"""OverBot's server ID."""
support_server_id = 550685823784321035

"""Test guild for app commands testing and owner commands usage."""
test_guild_id = None

# ENDIGNORE

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
