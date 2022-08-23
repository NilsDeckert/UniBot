import codecs
import logging
from configparser import ConfigParser

import interactions
from discord.ext.commands import Cog, has_guild_permissions, errors

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


class Roles(interactions.Extension):
    def __init__(self, bot: UniBot):
        self.bot = bot
        self.config = ConfigParser(delimiters="=")
        self.config.read_file(codecs.open(Config.get_file(), "r", "utf8"))

    @interactions.extension_command(name="add_reaction_role", description="Add emoji to assign roll",
                                    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
                                    options=[
                                        interactions.Option(
                                            name="message_link",
                                            description="Message that serves as role message",
                                            type=interactions.OptionType.STRING,
                                            required=True
                                        ),
                                        interactions.Option(
                                            name="role",
                                            description="role that should be assigned",
                                            type=interactions.OptionType.ROLE,
                                            required=True
                                        ),
                                        interactions.Option(
                                            name="emoji",
                                            description="emoji that is used to assign the role",
                                            type=interactions.OptionType.STRING,
                                            required=True
                                        )
                                    ])
    async def add_reaction_role(self, ctx: interactions.CommandContext, message_link: str, role: str, emoji: str):
        guild_id = str(ctx.guild_id)

        if not self.config.has_section(guild_id):
            self.config.add_section(guild_id)

        if "https://discord.com/channels/" in message_link:

            # Get message object from link
            link = message_link.split('/')
            channel_id = int(link[5])
            msg_id = int(link[6])
            channel = self.bot.get_channel(channel_id)
            msg = await channel.fetch_message(msg_id)

            self.config.set(guild_id, f"{msg_id}_{emoji}", str(role))
            try:
                with open(Config.get_file(), 'w', encoding='utf-8') as f:
                    self.config.write(f)
                    logging.info(f"Added reaction role '{role}' to message {msg_id}")

                await msg.add_reaction(emoji)
                await ctx.send(f"Successfully added role \'{role}\'", ephemeral=True)
            except errors.HTTPException:
                self.config.remove_option(guild_id, str(emoji))
                with open(Config.get_file(), 'w', encoding='utf-8') as f:
                    self.config.write(f)
                await ctx.send("Error: Make sure you only use standard emojis or emojis from this server", ephemeral=True)
        else:
            await ctx.send("Error: Make sure you've got the right link", ephemeral=True)

    @interactions.extension_command(name="remove_reaction_role",
                                    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
                                    description="Add emoji to assign roll",
                                    options=[
                                        interactions.Option(
                                            name="message_link",
                                            description="Message that serves as role message",
                                            type=interactions.OptionType.STRING,
                                            required=True
                                        ),
                                        interactions.Option(
                                            name="emoji",
                                            description="emoji that is used to assign the role",
                                            type=interactions.OptionType.STRING,
                                            required=True
                                        )
                                    ])
    async def remove_reaction_role(self, ctx: interactions.CommandContext, message_link: str, emoji: str):
        guild_id = str(ctx.guild_id)

        if "https://discord.com/channels/" in message_link:

            # Get message object from link
            link = message_link.split('/')
            channel_id = int(link[5])
            msg_id = int(link[6])
            channel = self.bot.get_channel(channel_id)
            msg = await channel.fetch_message(msg_id)

            if not self.config.has_option(guild_id, f"{msg_id}_{emoji}"):
                await ctx.send(f"Could not find \'{emoji}\' role for this message", ephemeral=True)
                return

            self.config.remove_option(guild_id, f"{msg_id}_{emoji}")
            with open(Config.get_file(), 'w', encoding='utf-8') as f:
                self.config.write(f)

            await msg.clear_reaction(emoji)
            await ctx.send(f"Successfully removed \'{emoji}\' role", ephemeral=True)
        else:
            await ctx.send("Error: Make sure you've got the right link", ephemeral=True)
