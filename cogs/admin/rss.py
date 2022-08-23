import codecs
import logging
from configparser import ConfigParser

import discord
import feedparser
import html2text
import interactions
from discord.ext import tasks
from discord.ext.commands import Cog, has_guild_permissions

from cogs.user import tu_specific
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


class RSS(interactions.Extension):
    def __init__(self, bot: UniBot):
        self.bot = bot
        self.config = ConfigParser(delimiters="=")
        self.config.read_file(codecs.open(Config.get_file(), "r", "utf8"))
        #self.check_feeds.start()

    # def cog_unload(self):
    #     self.check_feeds.cancel()

    @interactions.extension_command(name="add_rss_feed", description="Setup a rss feed for this channel",
                                    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
                                    options=[
                                        interactions.Option(
                                            name="feed_link",
                                            description="link to rss feed",
                                            type=interactions.OptionType.STRING,
                                            required=True
                                        ),
                                        interactions.Option(
                                            name="role",
                                            description="role to ping on rss update",
                                            type=interactions.OptionType.ROLE,
                                            required=False
                                        )
                                    ])
    async def add_rss_feed(self, ctx: interactions.CommandContext, feed_link: str, role: discord.role = None):
        guild_id = str(ctx.guild_id)
        channel_id = str(ctx.channel.id)

        if not self.config.has_section(guild_id):
            self.config.add_section(str(guild_id))

        if not self.config.has_option(guild_id, "rss_channels"):
            self.config.set(guild_id, "rss_channels", channel_id)
        else:
            channels = self.config.get(guild_id, "rss_channels").split(",")
            if channel_id not in channels:
                self.config.set(guild_id, "rss_channels",
                                f"{self.config.get(guild_id, 'rss_channels')},{channel_id}")

        self.config.set(guild_id, f"{channel_id}_link", feed_link)
        self.config.set(guild_id, f"{channel_id}_hash", "0")
        if role:
            self.config.set(guild_id, f"{channel_id}_role", role.name)

        with open(Config.get_file(), 'w', encoding="utf-8") as f:
            self.config.write(f)
            logging.info(f"{guild_id}: Added rss feed for channel {channel_id}")
        await ctx.send("Added new rss feed.", ephemeral=True)

    @interactions.extension_command(name="remove_rss_feed", description="Remove rss feed for this channel",
                                    default_member_permissions=interactions.Permissions.ADMINISTRATOR)
    async def remove_rss_feed(self, ctx: interactions.CommandContext):
        guild_id = str(ctx.guild_id)
        channel_id = str(ctx.channel.id)
        if self.config.has_section(guild_id):
            if self.config.has_option(guild_id, f"{channel_id}_link"):
                self.config.remove_option(guild_id, f"{channel_id}_link")
                self.config.remove_option(guild_id, f"{channel_id}_hash")
                if self.config.has_option(guild_id, f"{channel_id}_role"):
                    self.config.remove_option(guild_id, f"{channel_id}_role")

                rss_channels = self.config.get(guild_id, "rss_channels").split(",")
                rss_channels.remove(channel_id)
                rss_string = ""

                if len(rss_channels) == 0:
                    rss_string = ""
                elif len(rss_channels) == 1:
                    rss_string = str(rss_channels[0])
                else:
                    for channel in rss_channels[:-1]:
                        rss_string += str(channel) + ","

                    rss_string += rss_channels[-1]

                self.config.set(guild_id, "rss_channels", rss_string)

                with open(Config.get_file(), 'w', encoding="utf-8") as f:
                    self.config.write(f)
                logging.info("Removed rss feed for channel " + channel_id)
                await ctx.send("Removed rss feed for this channel", ephemeral=True)
        else:
            await ctx.send("No rss feed had been setup", ephemeral=True)

    @interactions.extension_command(name="set_rss_role",
                                    description="Set role that will be notified on new rss entries",
                                    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
                                    options=[
                                        interactions.Option(
                                            name="role",
                                            description="role to ping on rss update",
                                            type=interactions.OptionType.ROLE,
                                            required=True
                                        )
                                    ])
    async def set_rss_role(self, ctx: interactions.CommandContext, role: discord.role = None):
        guild_id = str(ctx.guild_id)
        channel_id = str(ctx.channel.id)
        if self.config.has_section(guild_id):
            self.config.set(guild_id, f"{channel_id}_role", role.name)
            with open(Config.get_file(), 'w', encoding="utf-8") as f:
                self.config.write(f)
            logging.info(f"Set role {role.name} as rss role for channel {channel_id}")
            await ctx.send(f"Role {role.name} will be notified on new rss entries", ephemeral=True)
        else:
            await ctx.send("No rss feed had been setup", ephemeral=True)

    @interactions.extension_command(name="remove_rss_role", description="Remove rss feed for this channel",
                                    default_member_permissions=interactions.Permissions.ADMINISTRATOR)
    async def remove_rss_role(self, ctx: interactions.CommandContext):
        guild_id = str(ctx.guild_id)
        channel_id = str(ctx.channel.id)
        if self.config.has_section(guild_id):
            if self.config.has_option(guild_id, f"{channel_id}_role"):
                self.config.remove_option(guild_id, f"{channel_id}_role")
                with open(Config.get_file(), 'w', encoding="utf-8") as f:
                    self.config.write(f)
                logging.info(f"Removed rss role for channel {channel_id}")
                await ctx.send("No role will be notified on new rss entries", ephemeral=True)
                return
        await ctx.send("No rss feed had been setup", ephemeral=True)

    @interactions.extension_command(name="load_rss", description="Load newest rss entry",
                                    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
                                    options=[
                                        interactions.Option(
                                            name="ping",
                                            description="ping according role",
                                            type=interactions.OptionType.BOOLEAN,
                                            required=False
                                        )
                                    ])
    async def load_rss(self, ctx: interactions.CommandContext, ping=False):
        guild_id = str(ctx.guild_id)
        channel_id = str(ctx.channel.id)

        if (not self.config.has_section(guild_id)) or (not self.config.has_option(guild_id, f"{channel_id}_link")):
            await ctx.send("No rss feed has been setup yet", ephemeral=True)
            return

        if ping and self.config.has_option(guild_id, f"{channel_id}_role"):
            role = self.config.get(guild_id, f"{channel_id}_role")
        else:
            role = None

        await ctx.send("Manually loaded entry:", ephemeral=True)  # Prevents "Interaction failed" message
        await send_rss_entry(self, int(channel_id), self.config.get(guild_id, f"{channel_id}_link"), role=role)

    # @tasks.loop(minutes=15.0)
    # async def check_feeds(self):
    #     for guild_id in self.config.sections():
    #         logging.info("Checking rss feed for server " + guild_id)
    #         if self.config.has_option(guild_id, "rss_channels"):
    #             channel_ids = self.config.get(guild_id, "rss_channels").split(",")
    #             for channel_id in channel_ids:
    #                 logging.info("Checking rss feed for channel " + str(channel_id))
    #                 link = self.config.get(guild_id, f"{channel_id}_link", fallback=None)
    #                 if not link:
    #                     continue
    #                 response = await tu_specific.TUB.get_server_status(self, link)
    #                 if response[0] != 200:
    #                     logging.error(f"Rss feed {link} returned code {response[0]}")
    #                     continue
    #                 d = feedparser.parse(link)
    #                 if not d.entries or len(d.entries) == 0:
    #                     logging.error("No rss entries found for link " + link)
    #                     continue
    #                 post = d.entries[0]
    #                 html = (post.summary.encode('utf-8', 'ignore').decode('utf-8'))
    #                 text = html2text.html2text(html)
    #                 text_hash = hash(text)
    #                 try:
    #                     # This check will always return true on first run, when PYTHONHASHSEED is not set
    #                     if not text_hash == self.config.getint(guild_id, f"{channel_id}_hash"):
    #                         if self.config.has_option(guild_id, f"{channel_id}_role"):
    #                             await send_rss_entry(self, int(channel_id),
    #                                                  self.config.get(guild_id, f"{channel_id}_link"),
    #                                                  self.config.get(guild_id, f"{channel_id}_role"))
    #                         else:
    #                             await send_rss_entry(self, int(channel_id),
    #                                                  self.config.get(guild_id, f"{channel_id}_link"))
    #                 except Exception as e:
    #                     logging.error(e)


# https://github.com/zenxr/discord_rss_bot
async def send_rss_entry(rss: RSS, channel_id: int, link: str, role: str = None):
    d = feedparser.parse(link)
    bot = rss.bot
    channel = bot.get_channel(channel_id)
    guild_id = channel.guild.id

    post = d.entries[0]
    title = (post.title.encode('utf-8', 'ignore').decode('utf-'))
    html = (post.summary.encode('utf-8', 'ignore').decode('utf-8'))
    text = html2text.html2text(html)
    text_hash = hash(text)
    link = post.link

    embed = discord.Embed(title=title)

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
        await channel.send(discord.utils.get(channel.guild.roles, name=role).mention, embed=embed)
    else:
        await channel.send(embed=embed)
