from . import rss

import discord
import interactions

import logging
from util.config import Config


async def set_role(bot, ctx: interactions.CommandContext, role: discord.role = None):
    guild_id = str(ctx.guild_id)
    channel_id = str(ctx.channel.id)
    if bot.config.has_section(guild_id):
        bot.config.set(guild_id, f"{channel_id}_role", role.name)
        with open(Config.get_file(), 'w', encoding="utf-8") as f:
            bot.config.write(f)
        logging.info(f"Set role {role.name} as rss role for channel {channel_id}")
        await ctx.send(f"Role {role.name} will be notified on new rss entries", ephemeral=True)
    else:
        await ctx.send("No rss feed had been setup", ephemeral=True)


async def remove(bot, ctx: interactions.CommandContext):
    guild_id = str(ctx.guild_id)
    channel_id = str(ctx.channel.id)
    if bot.config.has_section(guild_id):
        if bot.config.has_option(guild_id, f"{channel_id}_role"):
            bot.config.remove_option(guild_id, f"{channel_id}_role")
            with open(Config.get_file(), 'w', encoding="utf-8") as f:
                bot.config.write(f)
            logging.info(f"Removed rss role for channel {channel_id}")
            await ctx.send("No role will be notified on new rss entries", ephemeral=True)
            return
    await ctx.send("No rss feed had been setup", ephemeral=True)
