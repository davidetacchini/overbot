<p align="center">
  <img src="https://github.com" alt="OverBot Banner" width="300"/>
</p>
<h2 align="center">The best Overwatch bot for Discord.</h2>

<p align="center">
  <a href="https://github.com/davidetacchini/overbot/actions" traget="_blank">
    <img src="https://github.com/davidetacchini/overbot/workflows/Lint/badge.svg" alt="Lint Badge" />
  </a>
  <a href="https://github.com/psf/black" traget="_blank">
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code Style: Black" />
  </a>
  <a href="https://pycqa.github.io/isort/" target="_blank">
    <img src="https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336" alt="isort" />
  </a>
  <a href="https://pypi.org/project/py-cord/" traget="_blank">
    <img src="https://img.shields.io/pypi/v/py-cord?label=py-cord" alt="PyPI" />
  </a>
  <a href="https://ow-api.com/docs/" traget="_blank">
    <img src="https://img.shields.io/badge/API-ow--api-orange" alt="API" />
  </a>
  <a href="https://discord.com/invite/8g3jnxv" traget="_blank">
  <img src="https://discord.com/api/guilds/550685823784321035/embed.png" alt="Discord Server" />
  </a>
  <a href="https://top.gg/bot/547546531666984961" traget="_blank">
    <img src="https://top.gg/api/widget/servers/547546531666984961.svg?noavatar=true" alt="Server Count" />
  </a>
</p>

Self Hosting
------
I would appreciate if you don't host my bot.
However, if you want to test it out, the installation steps are as follows:

1. **Set up the PostgreSQL database by running the `psql` command**
```sql
CREATE DATABASE overbot;
CREATE USER davide WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE overbot TO davide;
```
Note: It is recommended to run the latest stable version of [PostgreSQL](https://www.postgresql.org/docs/release/)

2. **Set up the bot and run it**

**Linux**
```bash
git clone https://github.com/davidetacchini/overbot.git
cd overbot
python3 -m venv env
source env/bin/activate
pip install --upgrade pip setuptools # fix build failing
pip install -r requirements.txt
./scripts/init.sh
python3 bot.py
```

**MacOS and Windows**
1. Clone the repository
```bash
git clone https://github.com/davidetacchini/overbot.git
```
2. Load `schema.sql` to the *overbot* database
3. Setup a virtual environment
4. Install the dependencies
```bash
pip install -r requirements.txt
```
5. Rename `config.example.py` to `config.py`
6. Edit the `config.py` file
7. Use `python3 bot.py` to run the bot

Note: It is recommended to run the latest stable version of [Python](https://www.python.org/doc/versions/)

Contributing
------
OverBot uses [black](https://pypi.org/project/black/), [isort](https://pypi.org/project/isort/) and [flake8](https://pypi.org/project/flake8/) as code style.
If you want to contribute to OverBot, please run `./scripts/format.sh` before submitting any pull request.
