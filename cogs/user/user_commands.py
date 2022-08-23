import codecs
from configparser import ConfigParser

import interactions

from main import UniBot
from util.config import Config

guild_ids = Config.get_guild_ids()

#   --- Option Types ---

STRING = 3
INTEGER = 4
BOOLEAN = 5
USER = 6
CHANNEL = 7
ROLE = 8
MENTIONABLE = 9


class User(interactions.Extension):
    def __init__(self, bot: UniBot):
        self.client = bot
        self.config = ConfigParser(delimiters="=")
        self.config.read_file(codecs.open(Config.get_file(), "r", "utf8"))

    @interactions.extension_command(
        name="ping",
        description="Pong!"
    )
    async def ping(self, ctx: interactions.CommandContext):
        await ctx.send("Pong!")
