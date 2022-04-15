import hikari
import tanjun
import os
import logging
import time
import Challenger.database as db
from Challenger.config import Config


def build_bot(token):
    bot = hikari.GatewayBot(token)

    client = build_client(bot)

    client.add_listener(hikari.StartingEvent, on_starting)
    client.add_listener(hikari.StartingEvent, on_started)

    client.load_modules("Challenger.plugins")

    return bot


def build_client(bot:hikari.GatewayBot):
    client = tanjun.Client.from_gateway_bot(bot)
    return client


async def on_guild_available(event:hikari.GuildAvailableEvent):
    DB = db.Session(event.guild_id)
    DB.init_database(event.guild.name)


async def on_starting(event:hikari.StartingEvent):
    logging.info("starting")


async def on_started(event:hikari.StartedEvent , client=tanjun.injected(type=tanjun.Client)):
    await client.declare_global_commands()

    if os.environ.get("ENVIRONMENT") == "production":
        await client.declare_global_commands()
    elif os.environ.get("ENVIRONMENT") == "development":
        await client.declare_global_commands(guild=Config.TESTING_GUILD_ID)