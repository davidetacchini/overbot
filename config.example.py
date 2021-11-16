"""Whether the version is realase or beta."""
DEBUG = True

"""The Bot token."""
token = "your_bot_token"

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

"""Top.gg authorization."""
top_gg = {
    "url": "",
    "token": "",
}

"""discord.bots.gg authorization."""
discord_bots = {
    "url": "",
    "token": "",
}

# ENDIGNORE

"""Premium consts."""
PREMIUM_COOLDOWN = 1.5
PREMIUM_PROFILES_LIMIT = 25

"""Base consts."""
BASE_COOLDOWN = 3.0
BASE_PROFILES_LIMIT = 5

"""The owner's ID."""
owner_id = 285502621295312896

"""The version of the Bot."""
version = "4.0.0"

"""Prefix used if custom is not set."""
default_prefix = "-"

"""Default color used on most of the embeds"""
main_color = 0xFFA657

# IGNORE

"""OverBot's server ID."""
support_server_id = 550685823784321035

"""Overwatch news feed channel."""
news_channel = 771489241288540220

# ENDIGNORE

"""Hero portrait URL."""
hero_url = "https://d1u1mce87gyfbn.cloudfront.net/hero/{}/hero-select-portrait.png"

"""Overwatch API url (unofficial)."""
base_url = "https://ow-api.com/v3/stats"

"""GitHub links."""
github = {
    "profile": "https://github.com/davidetacchini/",
    "repo": "https://github.com/davidetacchini/overbot",
}

"""Overwatch endpoints."""
overwatch = {
    "status": "https://downdetector.com/status/overwatch/",
    "patch": "https://playoverwatch.com/en-us/news/patch-notes/{}",
    "news": "https://playoverwatch.com/en-us/news/",
    "player": "https://playoverwatch.com/en-us/career/{}/{}/",
    "account": "https://playoverwatch.com/en-us/search/account-by-name",
    "hero": "https://playoverwatch.com/en-us/heroes",
    "map": "https://playoverwatch.com/en-us/maps",
}

"""Official website."""
website = "https://overbot.netlify.app"

"""Official support server invite."""
support = "https://discord.gg/8g3jnxv"

"""Invite link."""
invite = "https://discord.com/oauth2/authorize?client_id=547546531666984961&permissions=134506560&scope=bot"

"""Vote link."""
vote = "https://top.gg/bot/547546531666984961/vote"

"""Premium URL."""
premium = "https://overbot.netlify.app/premium"

"""Guilds to ignore when getting data from the database."""
ignored_guilds = (
    550685823784321035,
    638339745117896745,
    110373943822540800,
)
