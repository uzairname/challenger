import hikari
import tanjun
import os
import logging
import time
from Challenger.database import Session
from Challenger.config import Config


def build_client(bot:hikari.GatewayBot):
    client = tanjun.Client.from_gateway_bot(bot)
    return client


def build_bot():
    bot = hikari.GatewayBot(os.environ.get("DISCORD_TOKEN"))

    client = build_client(bot)
    client.add_listener(hikari.StartingEvent, on_starting)

    client.load_modules("Challenger.plugins")

    return bot

async def on_started(event, client=tanjun.injected(type=tanjun.Client)):
    await client.declare_global_commands()



async def on_starting(event):
    logging.info("starting")

async def on_guild_available(event: hikari.GuildAvailableEvent):
    DB = Session(event.guild_id)
    DB.init_database()
    DB.update_guild_name(event.guild.name)