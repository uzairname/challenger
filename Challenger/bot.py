import hikari
import tanjun
import os
import logging
from datetime import datetime

from Challenger.database import Session
from Challenger.config import Config
from Challenger.utils.command_tools import on_error


def build_bot(token):
    bot = hikari.GatewayBot(token)

    bot.subscribe(hikari.GuildAvailableEvent, on_guild_available)

    client = build_client(bot)

    client.load_modules("Challenger.plugins")

    return bot


def build_client(bot:hikari.GatewayBot):
    client = tanjun.Client.from_gateway_bot(bot)

    client.add_client_callback(tanjun.abc.ClientCallbackNames.STARTING, on_starting)
    client.add_client_callback(tanjun.abc.ClientCallbackNames.STARTED, on_started)
    client.set_hooks(tanjun.Hooks().set_on_error(on_error))

    client.metadata["start_time"] = datetime.now()

    return client


async def on_guild_available(event:hikari.GuildAvailableEvent):
    print(event.guild.name)
    DB = Session(event.guild_id)
    DB.init_database(event.guild.name)


async def on_starting():
    logging.info("Starting")


async def on_started(client=tanjun.injected(type=tanjun.Client)):

    logging.info("Started")

    if os.environ.get("ENVIRONMENT") == "production":
        await client.declare_global_commands()
    elif os.environ.get("ENVIRONMENT") == "development":
        client.load_modules("Challenger.plugins.testing")
        await client.declare_global_commands(guild=Config.TESTING_GUILD_ID)