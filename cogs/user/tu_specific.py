import asyncio
import codecs
import logging
from configparser import ConfigParser

import discord
from discord.ext.commands import Cog
from discord_slash import SlashContext, cog_ext
import httpx

from main import UniBot
from util.config import Config

guild_ids = Config.get_guild_ids()


class TUB(Cog):
    def __init__(self, bot: UniBot):
        self.bot = bot
        self.config = ConfigParser(delimiters="=")
        self.config.read_file(codecs.open(Config.get_file(), "r", "utf8"))

    async def get_server_status(self, domain : str, timeout = 2):
        status = None
        error_message = None
        try:
            r : httpx.Response = await self.bot.httpxClient.get(
                domain,
                timeout=timeout
            )
            status = r.status_code
        except Exception as e:
            if isinstance(e, asyncio.TimeoutError):
                error_message = "Connection timed out."
            else:
                error_message = type(e).__name__

        return status, error_message

    @staticmethod
    def build_embed(title, url, status, error_message):
        if error_message:
            embed = discord.Embed(title=f"{title} Server Status", color=0xff0000, url=url)
            embed.add_field(name="Error", value=f"{error_message}", inline=False)
        else:
            embed = discord.Embed(title=f"{title} Server Status", color=0x00ff00,
                                  url=url)
            embed.add_field(name=title, value=f"{status}", inline=True)

        return embed

    @cog_ext.cog_slash(name="isis", guild_ids=guild_ids, description="Get ISIS and SHIBBOLETH server status")
    async def isis(self, ctx):
        (isis_status, error_message_isis), (shibboleth_status, error_message_shibboleth) = await asyncio.gather(
            self.get_server_status(
                domain="https://isis.tu-berlin.de"
            ),
            self.get_server_status(
                domain="https://shibboleth.tubit.tu-berlin.de/idp/profile/SAML2/Redirect/SSO?execution=e1s1"
            )
        )

        match (error_message_isis, error_message_shibboleth):
            case (None, None):
                match (isis_status, shibboleth_status):
                    case (200, 200):
                        color = 0x00ff00
                    case (200, _) | (_, 200):
                        color = 0xFFAD00
                    case _:
                        color = 0xFF0000

            case (_, None):
                isis_status = error_message_isis
                color = 0xFFAD00

            case (None, _):
                shibboleth_status = error_message_shibboleth
                color = 0xFFAD00

            case (_, _):
                isis_status = error_message_isis
                shibboleth_status = error_message_shibboleth
                color = 0xff0000

        embed = discord.Embed(title="ISIS and Shibboleth Server Status", color=color, url="https://isis.tu-berlin.de")
        embed.add_field(name="ISIS", value=f"{isis_status}", inline=True)
        embed.add_field(name="Shibboleth", value=f"{shibboleth_status}", inline=True)
        await ctx.send(embed=embed, hidden=False)

    @cog_ext.cog_slash(name="autolab", guild_ids=guild_ids, description="Get Autolab server status")
    async def autolab(self, ctx: SlashContext):
        status, error_message = await self.get_server_status(
            domain="https://autolab.service.tu-berlin.de/"
        )

        embed = self.build_embed("Autolab", "https://autolab.service.tu-berlin.de/", status, error_message)
        await ctx.send(embed=embed, hidden=False)

    @cog_ext.cog_slash(name="moses", guild_ids=guild_ids, description="Get Moses server status")
    async def moses(self, ctx: SlashContext):
        domain = "https://moseskonto.tu-berlin.de/moses/index.html"
        status, error_message = await self.get_server_status(
            domain=domain
        )

        embed = self.build_embed("Moses", domain, status, error_message)
        await ctx.send(embed=embed, hidden=False)

    @cog_ext.cog_slash(name="printer", guild_ids=guild_ids, description="Get status of CG's printer")
    async def printer(self, ctx: SlashContext):
        status, error_message = await self.get_server_status(
            domain="http://printer.cg.tu-berlin.de"
        )

        if error_message:
            embed = discord.Embed(title="Printer Status", color=0xff0000)
            embed.add_field(name="Error", value=f"{error_message}", inline=False)
        else:
            embed = discord.Embed(title="Printer Status", color=0x00ff00)
            embed.add_field(name="Printer",
                            value=f"Der Drucker des Fachbereichs Computer Graphics ist online :) \n{status}",
                            inline=False)
        await ctx.send(embed=embed, hidden=False)