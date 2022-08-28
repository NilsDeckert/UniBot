import codecs
import logging
from configparser import ConfigParser
from typing import Optional
import sentry_sdk
import interactions

import aiohttp
import discord
from discord.ext.commands import Bot
#from discord_slash import SlashCommand

from util.config import Config

#   --- Config ---

TOKEN = Config.get_token()
DATA_DIR = Config.get_data_dir()
SENTRY_DSN = Config.get_sentry_dsn()

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0
    )

config = ConfigParser(delimiters="=")
try:
    config.read_file(codecs.open(Config.get_file(), "r", "utf8"))
except FileNotFoundError:
    fp = open(Config.get_file(), 'x')
    fp.close()
    config.read_file(codecs.open(Config.get_file(), "r", "utf8"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%d.%m.%Y %H:%M:%S")


class UniBot(interactions.Client):
    def __init__(self, token):
        self.aiohttp_session: Optional[aiohttp.ClientSession] = None
        intents = interactions.Intents.ALL
        super().__init__(token=token, intents=intents)

    async def on_ready(self):
        print("Ready")
        logging.info(f"Startup as {self.user} / {self.user.id}")

    async def register_aiohttp_session(self):
        self.aiohttp_session = aiohttp.ClientSession()

    def load_cogs(self) -> None:
        logging.info("loading extensions...")
        self.load(name="cogs.user", package="cogs.user")
        self.load(name="cogs.listeners", package="cogs.listeners")
        self.load(name="cogs.admin", package="cogs.admin")
        logging.info("loaded extensions")

    def run_bot(self):
        logging.info("starting up...")
        self.load_cogs()
        self._loop.create_task(self.register_aiohttp_session())
        super().start()


def main():
    bot = UniBot(TOKEN)
    bot.run_bot()


if __name__ == "__main__":
    main()
