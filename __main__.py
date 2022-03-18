import os
from __init__ import *
import logging
import hikari
import tanjun
import time
from database import Database
import pandas as pd


DB = Database()

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
        self.client.load_modules("plugins.util", "plugins.queue", "plugins.demo", "plugins.player", "plugins.management")

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
        DB.open_connection(event.guild_id)

        # DB.update_config_table()

        DB.close_connection()
        pass



if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option("max_colwidth", 40)
    pd.options.display.width = 0

    DB.setup(TESTING_GUILD_ID)

    bot = PelaBot(os.environ.get("PELA_TOKEN"))
    bot.run()