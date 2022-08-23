from main import UniBot

from .admin_commands import Admin
from .roles import Roles
from .rss import RSS
from .watch_user import WatchUser


def setup(bot: UniBot):
    Admin(bot)
    Roles(bot)
    RSS(bot)
    WatchUser(bot)
