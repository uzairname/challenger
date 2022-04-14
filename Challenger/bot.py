import hikari
import os
from database import Database
import logging
from config import *
import time


#
# def run_bot():
#     bot = hikari.GatewayBot(os.environ.get("BOT_TOKEN"))
#
#     bot.subscribe(hikari.StartingEvent, on_starting)
#     bot.subscribe(hikari.StartedEvent, on_started)
#     bot.subscribe(hikari.GuildAvailableEvent, on_guild_available)
#
#
#     bot.run()
#
#
# async def on_started(event):
#     start_time = time.time()
#
#     await self.rest.edit_my_user(username="Challenger")
#
#     if os.environ.get('DSP') == "Production":
#         logging.info("Bot is in the production environment")
#         await self.client.declare_global_commands(force=True)
#     else:
#         logging.info("Bot is in a testing environment")
#         self.client.load_modules("plugins.demo")
#         await self.client.declare_global_commands(guild=Config.TESTING_GUILD_ID, force=True)
#
#
#
# async def on_starting(event):
#     logging.info("starting")
#
# async def on_guild_available(event: hikari.GuildAvailableEvent):
#     DB = Database(event.guild_id)
#     DB.init_database()
#     DB.update_guild_name(event.guild.name)