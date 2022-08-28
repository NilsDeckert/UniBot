import asyncio
import codecs
import logging
from configparser import ConfigParser

import discord
import feedparser
import html2text
import interactions
from interactions.client.get import get
from interactions.api.models import channel
from interactions.ext.tasks import IntervalTrigger, create_task

# from rss_feed import add_rss_feed
from . import rss_feed, rss_role

# from discord.ext import tasks
# from discord.ext.commands import Cog, has_guild_permissions

from cogs.user import tu_specific
from main import UniBot
from util.config import Config

guild_ids = Config.get_guild_ids()


class RSS(interactions.Extension):
    def __init__(self, bot: UniBot):
        self.bot: UniBot = bot
        self.config = ConfigParser(delimiters="=")
        self.config.read_file(codecs.open(Config.get_file(), "r", "utf8"))
        self.check_feeds.start(self)

    # def cog_unload(self):
    #     self.check_feeds.cancel()

    @interactions.extension_command(name="rss_feed", description="Invisible",
                                    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
                                    options=[
                                        interactions.Option(
                                            name="add",
                                            description="Add rss feed for this channel",
                                            type=interactions.OptionType.SUB_COMMAND,
                                            options=[
                                                interactions.Option(
                                                    name="link",
                                                    description="Link to the rss feed",
                                                    type=interactions.OptionType.STRING,
                                                    required=True
                                                ),
                                                interactions.Option(
                                                    name="role",
                                                    description="Role to ping on rss update",
                                                    type=interactions.OptionType.ROLE,
                                                    required=False
                                                )
                                            ]
                                        ),
                                        interactions.Option(
                                            name="remove",
                                            description="Remove rss feed from this channel",
                                            type=interactions.OptionType.SUB_COMMAND,
                                        ),
                                        interactions.Option(
                                            name="load",
                                            description="Manually load rss feed",
                                            type=interactions.OptionType.SUB_COMMAND,
                                            options=[
                                                interactions.Option(
                                                    name="ping",
                                                    description="Ping according role",
                                                    type=interactions.OptionType.BOOLEAN,
                                                    required=False
                                                )
                                            ]
                                        )
                                    ])
    async def rss_feed(self, ctx: interactions.CommandContext, sub_command: str,
                       link: str = None, role: interactions.Role = None, ping: bool = False):
        match sub_command:
            case "add":
                await rss_feed.add(self, ctx, link, role)
            case "remove":
                await rss_feed.remove(self, ctx)
            case "load":
                await rss_feed.load(self, ctx, ping)

    @interactions.extension_command(name="rss_role", description="Invisible",
                                    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
                                    options=[
                                        interactions.Option(
                                            name="set",
                                            description="Set role",
                                            type=interactions.OptionType.SUB_COMMAND,
                                            options=[
                                                interactions.Option(
                                                    name="role",
                                                    description="Role to ping on update",
                                                    type=interactions.OptionType.ROLE,
                                                    required=True
                                                )
                                            ]
                                        ),
                                        interactions.Option(
                                            name="remove",
                                            description="Remove role",
                                            type=interactions.OptionType.SUB_COMMAND
                                        )
                                    ])
    async def rss_role(self, ctx: interactions.CommandContext, sub_command: str, role: interactions.Role = None):
        match sub_command:
            case "set":
                await rss_role.set_role(self, ctx, role)
            case "remove":
                await rss_role.remove(self, ctx)

    @create_task(IntervalTrigger(60 * 15))
    async def check_feeds(self):
        for guild_id in self.config.sections():
            logging.info("Checking rss feed for server " + guild_id)
            if self.config.has_option(guild_id, "rss_channels"):
                channel_ids = self.config.get(guild_id, "rss_channels").split(",")
                for channel_id in channel_ids:
                    logging.info("Checking rss feed for channel " + str(channel_id))
                    link = self.config.get(guild_id, f"{channel_id}_link", fallback=None)
                    if not link:
                        continue
                    response = await tu_specific.TUB.get_server_status(self, link)
                    if response[0] != 200:
                        logging.error(f"Rss feed {link} returned code {response[0]}")
                        continue
                    d = feedparser.parse(link)
                    if not d.entries or len(d.entries) == 0:
                        logging.error("No rss entries found for link " + link)
                        continue
                    post = d.entries[0]
                    html = (post.summary.encode('utf-8', 'ignore').decode('utf-8'))
                    text = html2text.html2text(html)
                    text_hash = hash(text)
                    try:
                        # This check will always return true on first run, when PYTHONHASHSEED is not set
                        if not text_hash == self.config.getint(guild_id, f"{channel_id}_hash"):
                            if self.config.has_option(guild_id, f"{channel_id}_role"):
                                await send_rss_entry(self, int(guild_id), int(channel_id),
                                                     self.config.get(guild_id, f"{channel_id}_link"),
                                                     self.config.get(guild_id, f"{channel_id}_role"))
                            else:
                                await send_rss_entry(self, int(guild_id), int(channel_id),
                                                     self.config.get(guild_id, f"{channel_id}_link"))
                    except Exception as e:
                        logging.error(e)


# https://github.com/zenxr/discord_rss_bot
async def send_rss_entry(rss: RSS, guild_id: int, channel_id: int, link: str, role: str = None):
    d = feedparser.parse(link)
    bot: interactions.Client = rss.bot
    # channel: interactions.Channel = await get(bot, interactions.Channel, object_id=channel_id, parent_id=guild_id)
    channel: interactions.Channel = await get(bot, interactions.Channel, object_id=channel_id)

    post = d.entries[0]
    title = (post.title.encode('utf-8', 'ignore').decode('utf-'))
    html = (post.summary.encode('utf-8', 'ignore').decode('utf-8'))
    text = html2text.html2text(html)
    text_hash = hash(text)
    link = post.link

    embed = interactions.Embed(title=title)

    if len(text) > 1024:
        text = text[:1018] + "\n[...]"

    if len(text) > 4:
        embed.add_field(name="Text:", value=text, inline=False)

    embed.add_field(name="Link: ", value=link, inline=False)

    logging.info(f"New rss entry for channel {channel_id}")
    rss.config.set(str(guild_id), f"{channel_id}_hash", str(text_hash))
    with open(Config.get_file(), 'w', encoding="utf-8") as f:
        rss.config.write(f)
        logging.info(f"{guild_id}: Updated rss hash for channel {channel_id}")
    if role:
        guild = await get(bot, interactions.Guild, object_id=guild_id)
        roles = interactions.search_iterable(await guild.get_all_roles(), name=role)
        logging.info(roles)
        await channel.send(
            roles[0].mention, embeds=embed)
    else:
        await channel.send(embeds=embed)
