import os
from __init__ import *
import logging
import hikari
import tanjun
import time
from database import Database
import pandas as pd

class PelaBot (hikari.GatewayBot):

    def __init__(self, token):
        super().__init__(token)

    def run(self):
        self.create_client()

        self.subscribe(hikari.StartedEvent, self.on_started)
        self.subscribe(hikari.GuildAvailableEvent, self.on_guild_available)

        activity=hikari.presences.Activity(name= "bloons", type=hikari.presences.ActivityType(value=3))

        super().run(activity=activity)

    def create_client(self):
        self.client = (tanjun.Client.from_gateway_bot(self))
        self.client.load_modules("plugins.util", "plugins.queue", "plugins.player", "plugins.management")
        self.client.set_auto_defer_after(1)

    async def on_started(self, event:hikari.StartedEvent):
        self.start_time = time.time()

        if os.environ.get('DSP') == "Production":
            logging.info("███ Bot is in the production environment")
            commands = await self.client.declare_global_commands(force=True)
            for command in commands:
                print("declared " + command.name)
        else:
            logging.info("███ Bot is in a testing environment")
            await self.rest.edit_my_member(guild=TESTING_GUILD_ID, nickname=f"Pela ({os.environ.get('DSP')})")
            commands = await self.client.declare_global_commands(guild=TESTING_GUILD_ID, force=True)
            for command in commands:
                print("declared " + command.name)


    async def on_guild_available(self, event: hikari.GuildAvailableEvent):
        DB = Database(event.guild_id)
        DB.init_database()


debug = (os.environ.get("DSP") == "testing")

if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option("max_colwidth", 90)
    pd.options.display.width = 100
    pd.options.mode.chained_assignment = None

    bot = PelaBot(os.environ.get("PELA_TOKEN"))

    if debug:
        DB = Database(TESTING_GUILD_ID)
        DB.setup_test()

    bot.run()