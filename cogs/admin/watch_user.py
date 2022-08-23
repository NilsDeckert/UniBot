import codecs
import json
from configparser import ConfigParser

import discord
import interactions
from discord.ext.commands import Cog, has_guild_permissions

from util.config import Config

guild_ids = Config.get_guild_ids()
from main import UniBot

#   --- Option Types ---

STRING = 3
INTEGER = 4
BOOLEAN = 5
USER = 6
CHANNEL = 7
ROLE = 8
MENTIONABLE = 9


class WatchUser(interactions.Extension):
    def __init__(self, bot: UniBot):
        self.bot = bot
        self.config = ConfigParser(delimiters="=")
        self.config.read_file(codecs.open(Config.get_file(), "r", "utf8"))

    @interactions.extension_command(name="watch", description="Add user to watch list",
                                    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
                                    options=[
                                        interactions.Option(
                                            name="user",
                                            description="User",
                                            type=interactions.OptionType.USER,
                                            required=True
                                        )
                                    ])
    async def watch(self, ctx: interactions.CommandContext, user: discord.User):
        guild_id = str(ctx.guild_id)
        if not self.config.has_section(guild_id):
            self.config.add_section(guild_id)

        watched_users = json.loads(self.config.get(guild_id, "watched_users", fallback="[]"))
        watched_dict = json.loads(self.config.get(guild_id, "watched_dict", fallback="{}"))

        if user.id in watched_users:
            await ctx.send(f"{user.mention} is already on the watch list", ephemeral=True)
        else:

            category_id = self.config.get(guild_id, "watch_category", fallback=None)
            valid_category = category_id and discord.utils.get(ctx.guild.categories, id=int(category_id))
            if not valid_category:
                await ctx.send("Please set a category for the new channels first. Use /watch_category.",
                               ephemeral=True)
            else:
                watch_category = discord.utils.get(ctx.guild.categories, id=int(category_id))
                new_channel = await ctx.guild.create_text_channel(name=f"{user.name}", category=watch_category)
                watched_dict[str(user.id)] = str(new_channel.id)

                watched_users.append(user.id)
                self.config.set(guild_id, "watched_users", str(watched_users))
                self.config.set(guild_id, "watched_dict", json.dumps(watched_dict))

                with open(Config.get_file(), 'w', encoding="utf-8") as f:
                    self.config.write(f)

                await new_channel.send(
                    f"{ctx.author.mention} added {user.mention} to the watch list. Use /unwatch to remove them.")
                await new_channel.send(
                    "Do not manually delete this channel. "
                    "It will be deleted automatically when the user gets removed from the watch list.")

                await ctx.send(f"Successfully added {user.mention} to watch list, see {new_channel.mention}",
                               ephemeral=True)

    @interactions.extension_command(name="unwatch", description="Remove user from watch list",
                                    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
                                    options=[
                                        interactions.Option(
                                            name="user",
                                            description="User",
                                            type=interactions.OptionType.USER,
                                            required=True
                                        ),
                                        interactions.Option(
                                            name="delete",
                                            description="Delete channel?",
                                            type=interactions.OptionType.BOOLEAN,
                                            required=True
                                        )
                                    ])
    async def unwatch(self, ctx: interactions.CommandContext, user: discord.User, delete: bool):
        guild_id = str(ctx.guild_id)

        watched_users = json.loads(self.config.get(guild_id, "watched_users", fallback="[]"))
        watched_dict = json.loads(self.config.get(guild_id, "watched_dict", fallback="{}"))

        if user.id not in watched_users:
            await ctx.send(f"{user.mention} is not on the watch list", ephemeral=True)
        else:

            watched_users.remove(user.id)
            channel_id = int(watched_dict.pop(str(user.id)))
            if delete:
                await ctx.guild.get_channel(channel_id).delete()
            else:
                await ctx.guild.get_channel(channel_id).send(
                    f"User {user.mention} has been removed from the watch list by {ctx.author.mention}."
                    f" You can delete this channel at any time.")

            self.config.set(guild_id, "watched_users", str(watched_users))
            self.config.set(guild_id, "watched_dict", json.dumps(watched_dict))

            with open(Config.get_file(), 'w', encoding="utf-8") as f:
                self.config.write(f)

            await ctx.send(f"Successfully removed {user.mention} from watch list", ephemeral=True)

    @interactions.extension_command(name="watched", description="Gets users that are on watch list",
                                    default_member_permissions=interactions.Permissions.ADMINISTRATOR, )
    async def watched(self, ctx: interactions.CommandContext):
        guild_id = str(ctx.guild_id)
        if not self.config.has_section(guild_id) or not self.config.has_option(guild_id, "watched_users"):
            await ctx.send("No watched users set", ephemeral=True)
        else:
            watched_users = json.loads(self.config.get(guild_id, "watched_users", fallback="[]"))
            watched_dict = json.loads(self.config.get(guild_id, "watched_dict", fallback="{}"))

            if len(watched_users) == 0:
                await ctx.send("No watched users", ephemeral=True)
            else:
                embed = discord.Embed(title="Watched users")
                too_long = len(watched_users) > 25
                if too_long:
                    watched_users = watched_users[:24]

                for user_id in watched_users:
                    user = self.bot.get_user(user_id)
                    if user:
                        embed.add_field(name=user.name,
                                        value=
                                        f"{user.mention} "
                                        f"({ctx.guild.get_channel(int(watched_dict[str(user.id)])).mention})",
                                        inline=False)
                    else:
                        embed.add_field(name=user_id,
                                        value=
                                        "User not found "
                                        f"({ctx.guild.get_channel(int(watched_dict.pop(str(user_id)))).mention})",
                                        inline=False)

                if too_long:
                    embed.add_field(name="...", value="...", inline=False)
                await ctx.send(embed=embed, ephemeral=True)

    @interactions.extension_command(name="watch_category", description="Set category for watch list",
                                    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
                                    options=[
                                        interactions.Option(
                                            name="category",
                                            description="Category",
                                            type=interactions.OptionType.CHANNEL,
                                            required=True
                                        )
                                    ])
    async def watch_category(self, ctx: interactions.CommandContext, category: discord.CategoryChannel):
        guild_id = str(ctx.guild_id)
        if not self.config.has_section(guild_id):
            self.config.add_section(guild_id)

        self.config.set(guild_id, "watch_category", str(category.id))

        with open(Config.get_file(), 'w', encoding="utf-8") as f:
            self.config.write(f)

        await ctx.send(f"Successfully set watch category to {category.mention}", ephemeral=True)
