import hikari
import tanjun
import os
from abc import ABC
import logging
import time
import pandas as pd

from __init__ import *
from config import Config
from database import Database



async def on_guild_available(event: hikari.GuildAvailableEvent):
    DB = Database(event.guild_id)
    DB.init_database()
    DB.update_guild_name(event.guild.name)


async def on_starting(event):
    logging.info("starting")


class Bot (hikari.GatewayBot, ABC):

    def __init__(self, token):
        super().__init__(token)
        self.client = None
        self.start_time = None

    def run(self, *args, **kwargs):
        self.create_client()

        self.subscribe(hikari.StartingEvent, on_starting)
        self.subscribe(hikari.StartedEvent, self.on_started)
        self.subscribe(hikari.GuildAvailableEvent, on_guild_available)

        activity=hikari.presences.Activity(name= "everything", type=hikari.presences.ActivityType.COMPETING)
        super().run(activity=activity)

    def create_client(self):
        self.client = (tanjun.Client.from_gateway_bot(self))
        self.client.load_modules("plugins.about", "plugins.queue", "plugins.player", "plugins.management", "plugins.matches", "plugins.misc")
        self.client.set_auto_defer_after(1) #TODO: remove

    async def on_started(self, event):
        self.start_time = time.time()

        await self.rest.edit_my_user(username="Challenger")

        if os.environ.get('DSP') == "Production":
            logging.info("Bot is in the production environment")
            await self.client.declare_global_commands(force=True)
        else:
            logging.info("Bot is in a testing environment")
            self.client.load_modules("plugins.demo")
            await self.client.declare_global_commands(guild=Config.testing_guild_id, force=True)


bot = Bot(os.environ.get('DISCORD_TOKEN'))

debug = (os.environ.get("DSP") == "testing")
if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option("max_colwidth", 190)
    pd.options.display.width = 100
    pd.options.mode.chained_assignment = None

    if debug:
        testing_DB = Database(Config.testing_guild_id)
        testing_DB.setup_test()

    bot.run()