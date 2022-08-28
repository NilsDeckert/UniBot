import codecs
import logging
from configparser import ConfigParser

import interactions
from interactions.client.get import get
from discord.ext.commands import Cog, has_guild_permissions, errors

from main import UniBot
from util.config import Config

guild_ids = Config.get_guild_ids()


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
    async def add_reaction_role(self, ctx: interactions.CommandContext, message_link: str, role: interactions.Role,
                                emoji: str):
        guild_id = str(ctx.guild_id)

        if not self.config.has_section(guild_id):
            self.config.add_section(guild_id)

        if "https://discord.com/channels/" not in message_link:
            await ctx.send("Error: Make sure you've got the right link", ephemeral=True)
            return

        guild_id, msg, msg_id = await self.msg_from_link(message_link)

        self.config.set(str(guild_id), f"{msg_id}_{emoji}", str(role.name))
        try:
            with open(Config.get_file(), 'w', encoding='utf-8') as f:
                self.config.write(f)
                logging.info(f"Added reaction role '{role.name}' to message {msg_id}")

            await msg.create_reaction(emoji)
            await ctx.send(f"Successfully added role \'{role.name}\'", ephemeral=True)

        except errors.HTTPException:
            self.config.remove_option(guild_id, str(emoji))
            with open(Config.get_file(), 'w', encoding='utf-8') as f:
                self.config.write(f)
            await ctx.send("Error: Make sure you only use standard emojis or emojis from this server",
                           ephemeral=True)

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
        if "https://discord.com/channels/" not in message_link:
            await ctx.send("Error: Make sure you've got the right link", ephemeral=True)
            return

        guild_id, msg, msg_id = await self.msg_from_link(message_link)

        if not self.config.has_option(str(guild_id), f"{msg_id}_{emoji}"):
            await ctx.send(f"Could not find \'{emoji}\' role for this message", ephemeral=True)
            return

        self.config.remove_option(str(guild_id), f"{msg_id}_{emoji}")
        with open(Config.get_file(), 'w', encoding='utf-8') as f:
            self.config.write(f)

        await msg.remove_all_reactions_of(emoji)
        await ctx.send(f"Successfully removed \'{emoji}\' role", ephemeral=True)

    async def msg_from_link(self, link) -> interactions.Message:
        assert "https://discord.com/channels/" in link, "Invalid link"
        link = link.split('/')
        guild_id, channel_id, msg_id = [int(x) for x in link[4:7]]

        channel = await get(self.bot, interactions.Channel, object_id=channel_id, parent_id=guild_id)
        msg = await channel.get_message(msg_id)
        return guild_id, msg, msg_id
