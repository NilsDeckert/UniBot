import codecs
import configparser
import os
import discord
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option
from discord.ext.commands import has_permissions
from dotenv import load_dotenv

from pytz import timezone
from datetime import datetime

import logging
from configparser import ConfigParser

#   --- Config ---

config = ConfigParser(delimiters="=")
config.read_file(codecs.open("config.ini", "r", "utf8"))

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

logging.basicConfig(level=logging.INFO)

#   --- Option Types ---

STRING = 3
INTEGER = 4
BOOLEAN = 5
USER = 6
CHANNEL = 7
ROLE = 8
MENTIONABLE = 9


#   --- Events ---

class MyClient(discord.Client):
    async def on_ready(self):
        print("Bot ist online!")

    async def on_message(self, message: discord.Message):

        logging.info(message.content)

        if message.author.id == client.user.id:
            return

        if "plagiat" in message.content.lower():
            await message.add_reaction("🚨")

    # Ctrl+C, Ctrl+V
    async def on_message_delete(self, message: discord.Message):
        guild_id = str(message.guild.id)
        if (not message.author.bot) and config.has_option(guild_id, "modlog"):
            try:
                async for entry in message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
                    author_can_delete_massages = message.author.permissions_in(message.channel).manage_messages
                    timestamp = entry.created_at.now(timezone("Europe/Berlin")).replace(tzinfo=None)
                    if author_can_delete_massages:
                        return
                    if (datetime.now() - timestamp).total_seconds() < 1.0:  # Custom time function

                        embed = discord.Embed(title="Message Deleted By Mod")
                        embed.add_field(name="Member: ", value=message.author.mention, inline=True)
                        embed.add_field(name="Mod: ", value=entry.user.mention, inline=True)

                        # Media might not have message content
                        if message.content:
                            embed.add_field(name="Message: ", value=message.content, inline=False)
                        else:
                            embed.add_field(name="Message: ", value="None", inline=False)

                        embed.add_field(name="Channel: ", value=message.channel.mention, inline=False)

                        # List of media urls, display first image
                        if message.attachments:
                            links = ""
                            for url in message.attachments:
                                links += str(url) + "\n"
                            embed.add_field(name="Media: ", value=links, inline=False)
                            embed.set_image(url=message.attachments[0])

                        modlog_id = config.get(guild_id, "modlog")
                        modlog = await client.fetch_channel(modlog_id)
                        await modlog.send(embed=embed)

            except discord.errors.Forbidden:
                logging.warning("Missing permissions for logging message deletion")

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == client.user.id:
            return

        guild_id = str(payload.guild_id)
        channel_id = str(payload.channel_id)
        message_id = str(payload.message_id)
        link = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
        emoji = str(payload.emoji)
        if config.has_option(guild_id, "role_message"):
            if (config.get(guild_id, "role_message") == link) and (config.has_option(guild_id, emoji)):
                guild = self.get_guild(int(guild_id))
                role_string = config.get(guild_id, emoji)
                role = discord.utils.get(guild.roles, name=role_string)
                member = await guild.fetch_member(payload.user_id)

                await member.add_roles(role)

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        guild_id = str(payload.guild_id)
        channel_id = str(payload.channel_id)
        message_id = str(payload.message_id)
        link = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
        emoji = str(payload.emoji)

        if config.has_option(guild_id, "role_message"):
            if (config.get(guild_id, "role_message") == link) and (config.has_option(guild_id, emoji)):
                guild = self.get_guild(int(guild_id))
                role_string = config.get(guild_id, emoji)
                role = discord.utils.get(guild.roles, name=role_string)
                member = await guild.fetch_member(payload.user_id)

                await member.remove_roles(role)


#   --- Client Setup ---

intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.messages = True
intents.emojis = True
client = MyClient(intents=intents)
guild_ids = [817865198676738109, 831428691870744576]
slash = SlashCommand(client, sync_commands=True)


#   --- Commands ---

@slash.slash(name="ping", guild_ids=guild_ids, description="Pong!")
async def ping(ctx: SlashContext):
    await ctx.send("Pong!")


try:
    @has_permissions(manage_roles=True)
    @slash.slash(name="set_role_message", guild_ids=guild_ids, description="Set message that is used to add roles",
                 options=[
                     create_option(
                         name="message_link",
                         description="link to the message",
                         option_type=STRING,
                         required=True
                     )
                 ])
    async def set_role_message(ctx: SlashContext, message_link: str):
        guild_id = str(ctx.guild_id)
        if "https://discord.com/channels/" in message_link:
            if not config.has_section(guild_id):
                config.add_section(str(guild_id))
            config.set(guild_id, "role_message", message_link)

            with open('config.ini', 'w', encoding="utf-8") as f:
                config.write(f)
                logging.info(f"{guild_id}: Set new role message to {message_link}")
            await ctx.send(f"Set role message to <{message_link}>.")
        else:
            await ctx.send("Error: Make sure you've got the right link")
except discord.ext.commands.errors.MissingPermissions:
    pass


@slash.slash(name="get_role_message", guild_ids=guild_ids, description="Returns link to role message")
async def get_role_message(ctx: SlashContext):
    try:
        await ctx.send(config.get(str(ctx.guild_id), "role_message"))

    except configparser.NoSectionError:
        await ctx.send("Not defined yet! Use 'set_role_message' first")


try:
    @has_permissions(manage_roles=True)
    @slash.slash(name="set_modlog", guild_ids=guild_ids, description="Sets channel that is used for logs",
                 options=[
                     create_option(
                         name="channel",
                         description="Channel",
                         option_type=CHANNEL,
                         required=True
                     )
                 ])
    async def set_role_message(ctx: SlashContext, channel: discord.TextChannel):
        guild_id = str(ctx.guild_id)
        if not config.has_section(guild_id):
            config.add_section(guild_id)

        config.set(guild_id, "modlog", str(channel.id))

        with open('config.ini', 'w', encoding="utf-8") as f:
            config.write(f)

        await ctx.channel.send(f"Successfully set {channel.mention} as modlog")

except discord.ext.commands.errors.MissingPermissions:
    pass

try:
    @has_permissions(manage_roles=True)
    @slash.slash(name="add_reaction_role", guild_ids=None, description="Add emoji to assign roll",
                 options=[
                     create_option(
                         name="role",
                         description="role that should be assigned",
                         option_type=ROLE,
                         required=True
                     ),
                     create_option(
                         name="emoji",
                         description="emoji that is used to assign the role",
                         option_type=STRING,
                         required=True
                     )
                 ])
    async def add_reaction_role(ctx: SlashContext, role: str, emoji: str):
        guild_id = str(ctx.guild_id)

        if not config.has_option(guild_id, "role_message"):
            await ctx.send("Please define a role message first. Use set_role_message")

        link = config.get(guild_id, "role_message").split('/')

        channel_id = int(link[5])
        msg_id = int(link[6])

        channel = client.get_channel(channel_id)
        msg = await channel.fetch_message(msg_id)

        config.set(guild_id, str(emoji), str(role))
        try:
            with open('config.ini', 'w', encoding='utf-8') as f:
                config.write(f)
            await msg.add_reaction(emoji)
            await ctx.send(f"Successfully added role \'{role}\'")
        except discord.errors.HTTPException:
            config.remove_option(guild_id, str(emoji))
            with open('config.ini', 'w', encoding='utf-8') as f:
                config.write(f)
            await ctx.send("Error: Make sure you only use standard emojis or emojis from this server")
except discord.ext.commands.errors.MissingPermissions:
    pass

client.run(TOKEN)
