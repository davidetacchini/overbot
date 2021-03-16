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

"""Webhook credentials."""
webhook = {
    "id": 0,
    "token": "",
}

"""OverBot private API used to share bot information to its website."""
obapi = {
    "url": "",
    "token": "",
}

"""Discord Bot List (top.gg) authorization."""
top_gg = {
    "url": "",
    "token": "",
}

"""Discord Bot List (discordbotlist.gg) authorization."""
dbl = {
    "url": "",
    "token": "",
}

"""discord.bots.gg authorization."""
discord_bots = {
    "url": "",
    "token": "",
}

# ENDIGNORE

"""Loading GIF"""
loading_gif = "https://i.imgur.com/DwjPYQn.gif"

"""The owner's ID."""
owner_id = 285502621295312896

"""The version of the Bot."""
version = "3.2.0"

"""Prefix used if custom is not set."""
default_prefix = "-"

"""Default color used on most of the embeds"""
main_color = 0xFA9C1D

# IGNORE

"""Channel ID for feedback logs."""
feedback_channel = 581888563256229891

"""Channel ID for error logs."""
errors_channel = 649188058574356481

"""OverBot's server ID."""
support_server_id = 550685823784321035

"""Overwatch news feed channel."""
news_channel = 771489241288540220

"""Bot status channel."""
status_channel = 784091607540039790

"""Channel ID for trivia submits."""
trivia_channel = 783149071217065985

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

"""Random endpoints."""
random = {
    "hero": "https://overwatch-api.tekrop.fr/heroes",
    "map": "https://playoverwatch.com/en-us/maps",
}

"""Overwatch endpoints."""
overwatch = {
    "status": "https://downdetector.com/status/overwatch/",
    "patch": "https://playoverwatch.com/en-us/news/patch-notes/{}",
    "news": "https://playoverwatch.com/en-us/news/",
    "player": "https://playoverwatch.com/en-us/career/{}/{}/",
    "account": "https://playoverwatch.com/en-us/search/account-by-name",
}

"""Python logo."""
python_logo = "https://i.imgur.com/6pg6Xv4.png"

"""Reddit logo."""
reddit_logo = "https://i.imgur.com/ZBwI6VN.png"

"""Official website."""
website = "https://overbot.netlify.app"

"""Official support server invite."""
support = "https://discord.gg/8g3jnxv"

"""Invite link."""
invite = "https://discord.com/api/oauth2/authorize?client_id=547546531666984961&permissions=134498368&scope=bot"

"""Vote link."""
vote = "https://top.gg/bot/547546531666984961/vote"

"""Ko-fi URL."""
kofi = "https://ko-fi.com/overbot"

"""Premium URL."""
premium = "https://overbot.netlify.app/premium"

"""Guilds to ignore when getting data from DB."""
ignored_guilds = (
    550685823784321035,
    638339745117896745,
    264445053596991498,
    110373943822540800,
)
