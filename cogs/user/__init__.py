from main import UniBot
from .tu_specific import TUB
from .user_commands import User


def setup(bot: UniBot):
    User(bot)
    TUB(bot)


