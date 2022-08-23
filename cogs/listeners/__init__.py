from main import UniBot

from .event_listeners import Listen


def setup(bot: UniBot):
    Listen(bot)
