import hikari
import tanjun
import os
import logging
import time
import pandas as pd
from Challenger.config import Config
import Challenger.database as db


# noinspection PyMethodMayBeStatic
class Bot (hikari.GatewayBot):

    def __init__(self, token):
        super().__init__(token)

    def run(self, *args, **kwargs):
        self.create_client()

        self.subscribe(hikari.StartingEvent, self.on_starting)
        self.subscribe(hikari.StartedEvent, self.on_started)
        self.subscribe(hikari.GuildAvailableEvent, self.on_guild_available)

        activity=hikari.presences.Activity(name= "everything", type=hikari.presences.ActivityType.COMPETING)
        super().run(activity=activity)

    def create_client(self):
        self.client = (tanjun.Client.from_gateway_bot(self))
        self.client.load_modules("Challenger.plugins.demo", "Challenger.plugins.queue", "Challenger.plugins.player", "Challenger.plugins.management", "Challenger.plugins.matches", "Challenger.plugins.misc")
        self.client.set_auto_defer_after(1) #TODO: remove

    async def on_started(self, event):
        self.start_time = time.time()

        await self.rest.edit_my_user(username="Challenger")

        if os.environ.get('DSP') == "Production":
            logging.info("Bot is in the production environment")
            await self.client.declare_global_commands(force=True)
        else:
            logging.info("Bot is in a testing environment")
            self.client.load_modules("Challenger.plugins.demo")
            await self.client.declare_global_commands(guild=Config.TESTING_GUILD_ID, force=True)

    async def on_guild_available(self, event: hikari.GuildAvailableEvent):
        DB = db.Session(event.guild_id)
        DB.init_database()
        DB.update_guild_name(event.guild.name)

    async def on_starting(self, event):
        logging.info("starting")


bot = Bot(os.environ.get('DISCORD_TOKEN'))
debug = (os.environ.get("DSP") == "Development")


from Challenger.bot import build_bot

if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option("max_colwidth", 190)
    pd.options.display.width = 100
    pd.options.mode.chained_assignment = None

    if debug:
        testing_DB = db.Session(Config.TESTING_GUILD_ID)
        testing_DB.setup_test()

    bot.run()
