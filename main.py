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
        # intents = discord.Intents.default()
        # intents.members = True
        # intents.reactions = True
        # intents.messages = True
        # intents.emojis = True
        # intents.bans = True
        #super().__init__(command_prefix="$", help_command=None, intents=intents)
        super().__init__(token=token, intents=intents)

    async def on_ready(self):
        print("Ready")
        logging.info(f"Startup as {self.user} / {self.user.id}")

    async def register_aiohttp_session(self):
        self.aiohttp_session = aiohttp.ClientSession()

    def load_cogs(self) -> None:
        self.load(name="cogs.user", package="cogs.user")
        self.load(name="cogs.listeners", package="cogs.listeners")
        self.load(name="cogs.admin", package="cogs.admin")
        # self.load_extension("cogs.user")
        # self.load_extension("cogs.listeners")
        # self.load_extension("cogs.admin")

        logging.info("loading extensions finished")

    def run_bot(self):
        logging.info("starting up...")
        self.load_cogs()
        #self.loop.create_task(self.register_aiohttp_session())
        self._loop.create_task(self.register_aiohttp_session())
        self.register_aiohttp_session()
        super().start()


def main():
    bot = UniBot(TOKEN)
    #slash = SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True, override_type=True)

    @bot.command(
        name="newtest",
        description="test",
        scope="951885887128629318"
    )
    async def newtest(ctx: interactions.CommandContext):
        await ctx.send("hi there")

    bot.run_bot()


if __name__ == "__main__":
    main()
