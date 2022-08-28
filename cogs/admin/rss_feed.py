from . import rss

import discord
import interactions

import logging
from util.config import Config


async def add(bot, ctx: interactions.CommandContext, feed_link: str, role: discord.role = None):
    guild_id = str(ctx.guild_id)
    channel_id = str(ctx.channel.id)

    if not bot.config.has_section(guild_id):
        bot.config.add_section(str(guild_id))

    if not bot.config.has_option(guild_id, "rss_channels"):
        bot.config.set(guild_id, "rss_channels", channel_id)
    else:
        channels = bot.config.get(guild_id, "rss_channels").split(",")
        if channel_id not in channels:
            bot.config.set(guild_id, "rss_channels",
                           f"{bot.config.get(guild_id, 'rss_channels')},{channel_id}")

    bot.config.set(guild_id, f"{channel_id}_link", feed_link)
    bot.config.set(guild_id, f"{channel_id}_hash", "0")
    if role:
        bot.config.set(guild_id, f"{channel_id}_role", role.name)

    with open(Config.get_file(), 'w', encoding="utf-8") as f:
        bot.config.write(f)
        logging.info(f"{guild_id}: Added rss feed for channel {channel_id}")
    await ctx.send("Added new rss feed.", ephemeral=True)


async def remove(bot, ctx: interactions.CommandContext):
    guild_id = str(ctx.guild_id)
    channel_id = str(ctx.channel.id)
    if bot.config.has_section(guild_id):
        if bot.config.has_option(guild_id, f"{channel_id}_link"):
            bot.config.remove_option(guild_id, f"{channel_id}_link")
            bot.config.remove_option(guild_id, f"{channel_id}_hash")
            if bot.config.has_option(guild_id, f"{channel_id}_role"):
                bot.config.remove_option(guild_id, f"{channel_id}_role")

            rss_channels = bot.config.get(guild_id, "rss_channels").split(",")
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

            bot.config.set(guild_id, "rss_channels", rss_string)

            with open(Config.get_file(), 'w', encoding="utf-8") as f:
                bot.config.write(f)
            logging.info("Removed rss feed for channel " + channel_id)
            await ctx.send("Removed rss feed for this channel", ephemeral=True)
    else:
        await ctx.send("No rss feed had been setup", ephemeral=True)


async def load(bot, ctx: interactions.CommandContext, ping=False):
    guild_id = str(ctx.guild_id)
    channel_id = str(ctx.channel.id)
    logging.info(guild_id)
    logging.info(channel_id)

    if (not bot.config.has_section(guild_id)) or (not bot.config.has_option(guild_id, f"{channel_id}_link")):
        await ctx.send("No rss feed has been setup yet", ephemeral=True)
        return

    if ping and bot.config.has_option(guild_id, f"{channel_id}_role"):
        role = bot.config.get(guild_id, f"{channel_id}_role")
    else:
        role = None

    await ctx.send("Manually loaded entry:", ephemeral=True)  # Prevents "Interaction failed" message
    await rss.send_rss_entry(bot, ctx.guild_id, int(channel_id), bot.config.get(guild_id, f"{channel_id}_link"),
                             role=role)
