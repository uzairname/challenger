from abc import ABC

import hikari
import tanjun

import time
import logging
import os
from __init__ import *
from database import Database

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

        self.client.load_modules("plugins.util", "plugins.queue", "plugins.demo", "plugins.player")
        pass

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
        # DB.open_connection(event.guild_id)
        #
        # DB.close_connection()
        pass


def build_bot(token) -> hikari.GatewayBot:
    bot = hikari.GatewayBot(token)

    client = (tanjun.Client.from_gateway_bot(bot))

    client.load_modules("plugins.util", "plugins.queue", "plugins.demo", "plugins.player")

    @bot.listen(hikari.StartedEvent)
    async def bot_started(event: hikari.StartedEvent):

        PelaBot.start_time = time.time()

        if os.environ.get('DSP') == "Production":
            logging.info("███ Bot is in the production environment")
            commands = await client.declare_global_commands(force=True)
            for command in commands:
                print("declared " + command.name)
        else:
            logging.info("███ Bot is in a testing environment")
            await bot.rest.edit_my_member(guild=TESTING_GUILD_ID, nickname=f"Pela ({os.environ.get('DSP')})")
            commands = await client.declare_global_commands(guild=TESTING_GUILD_ID, force=True)
            for command in commands:
                print("declared " + command.name)

    @bot.listen(hikari.GuildAvailableEvent)
    async def guild_available(event: hikari.GuildAvailableEvent):
        # DB.open_connection(event.guild_id)
        #
        # DB.close_connection()
        pass

    return bot