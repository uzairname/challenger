import os

from __init__ import *
from config import Config
import logging
import hikari
import tanjun
import time
from database import Database
import pandas as pd

from utils.utils import *

class Bot (hikari.GatewayBot):

    def __init__(self, token):
        super().__init__(token)

    def run(self):
        self.create_client()

        self.subscribe(hikari.StartingEvent, self.on_starting)
        self.subscribe(hikari.StartedEvent, self.on_started)
        self.subscribe(hikari.GuildAvailableEvent, self.on_guild_available)

        activity=hikari.presences.Activity(name= "bloons!", type=hikari.presences.ActivityType(value=5))

        super().run(activity=activity)

    def create_client(self):
        self.client = (tanjun.Client.from_gateway_bot(self))
        self.client.load_modules("plugins.about", "plugins.queue", "plugins.player", "plugins.management", "plugins.matches")
        self.client.set_auto_defer_after(1)

    async def on_starting(self, event):
        logging.info("█ starting")

    async def on_started(self, event):
        self.start_time = time.time()

        if os.environ.get('DSP') == "Production":
            logging.info("███ Bot is in the production environment")
            commands = await self.client.declare_global_commands(force=True)
            for command in commands:
                print("declared " + command.name)
        else:
            logging.info("███ Bot is in a testing environment")

            self.client.load_modules("plugins.demo")

            await self.rest.edit_my_member(guild=TESTING_GUILD_ID, nickname=f"vibing :p")
            commands = await self.client.declare_global_commands(guild=TESTING_GUILD_ID, force=True)
            for command in commands:
                print("declared " + command.name)


    async def on_guild_available(self, event: hikari.GuildAvailableEvent):
        DB = Database(event.guild_id)
        DB.init_database()

bot = Bot(os.environ.get('DISCORD_TOKEN'))

debug = (os.environ.get("DSP") == "testing")
if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option("max_colwidth", 90)
    pd.options.display.width = 100
    pd.options.mode.chained_assignment = None

    # bot = PelaBot(os.environ.get("DISCORD_TOKEN"))

    if debug:

        DB = Database(Config.testing_guild_id)
        DB.setup_test()

    bot.run()