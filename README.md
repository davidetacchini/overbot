![OverBot image](https://cdn.discordapp.com/attachments/646617232931160084/705411294596956293/overbot-banner_copy.png)
<h2 align="center">The best Overwatch bot for Discord.</h2>

<p align="center">
  <a href="https://travis-ci.org/github/davidetacchini/overbot/builds/" traget="_blank">
    <img src="https://travis-ci.com/davidetacchini/overbot.svg?branch=next" alt="Build">
  </a>
  <a href="https://github.com/psf/black" traget="_blank">
    <img alt="Code Style: Black" src="https://img.shields.io/badge/code%20style-black-000000.svg">
  </a>
  <a href="https://pypi.org/project/discord.py/" traget="_blank">
    <img alt="PyPI" src="https://img.shields.io/pypi/v/discord.py?label=discord.py">
  </a>
  <a href="https://ow-api.com/docs/" traget="_blank">
    <img alt="API" src="https://img.shields.io/badge/API-ow--api-orange">
  </a>
  <a href="https://discordapp.com/invite/8g3jnxv" traget="_blank">
  <img alt="Discord" src="https://img.shields.io/discord/550685823784321035"> 
  </a>
  <a href="https://top.gg/bot/547546531666984961" traget="_blank">
    <img src="https://top.gg/api/widget/servers/547546531666984961.svg?noavatar=true" alt="Server Count" />
  </a>
</p>


Self Hosting
------
I would appreciate if you don't host my bot.
However, if you want to test it out, the installation steps are as follows:
1. Setup the PostgreSQL database by running the `psql` command
```sql
CREATE DATABASE overbot;
CREATE user [username] WITH PASSWORD [password]
GRANT ALL PRIVILEGES ON DATABASE overbot TO [username]
```
Note: make sure you have PostgreSQL 9.5 (or higher) installed

2. Setup the bot and run it
```sh
git clone https://github.com/davidetacchini/overbot.git
cd overbot
python3 -m venv env
source env/bin/activate
./scripts/init.sh
systemctl start overbot
```
Note: make sure you have python3.6 (or higher) installed.

Code Style
------
OverBot uses [black](https://pypi.org/project/black/), [isort](https://pypi.org/project/isort/) and [flake8](https://pypi.org/project/flake8/) as code style.
If you want to contribute to OverBot, please run `./scripts/format.sh` before submitting any pull request.


