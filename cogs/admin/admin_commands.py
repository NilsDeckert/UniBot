import codecs
from configparser import ConfigParser

import discord
from discord.ext.commands import Cog, has_guild_permissions

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


class Admin(interactions.Extension):
    def __init__(self, bot: UniBot):
        self.bot = bot
        self.config = ConfigParser(delimiters="=")
        self.config.read_file(codecs.open(Config.get_file(), "r", "utf8"))

    #   --- MODLOG ---
    @interactions.extension_command(name="set_modlog", description="Sets channel that is used for logs",
                                    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
                                    options=[
                                        interactions.Option(
                                            name="channel",
                                            description="Channel",
                                            type=interactions.OptionType.CHANNEL,
                                            required=True
                                        )
                                    ])
    async def set_modlog(self, ctx: interactions.CommandContext, channel: discord.TextChannel):
        guild_id = str(ctx.guild_id)
        if not self.config.has_section(guild_id):
            self.config.add_section(guild_id)

        self.config.set(guild_id, "modlog", str(channel.id))

        with open(Config.get_file(), 'w', encoding="utf-8") as f:
            self.config.write(f)

        await ctx.send(f"Successfully set {channel.mention} as modlog", ephemeral=True)

    @interactions.extension_command(name="get_modlog", description="Gets channel that is used for logs")
    async def get_modlog(self, ctx: interactions.CommandContext):
        guild_id = str(ctx.guild_id)
        if not self.config.has_section(guild_id) or not self.config.has_option(guild_id, "modlog"):
            await ctx.send("No modlog set", ephemeral=True)
        else:
            channel_id = self.config.get(guild_id, "modlog")
            channel = ctx.guild.get_channel(int(channel_id))
            await ctx.send(f"Modlog is set to {channel.mention}", ephemeral=True)
