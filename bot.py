import hikari
import tanjun

import time

import logging
import os
from __init__ import *

class Bot:
    start_time = None

def build_bot(token) -> hikari.GatewayBot:
    bot = hikari.GatewayBot(token)

    client = (
        tanjun.Client.from_gateway_bot(
            bot,
            mention_prefix=True
        )
    )

    client.load_modules("plugins.util", "plugins.queue", "plugins.suggestions")  #, "plugins.embeds")

    @bot.listen(hikari.StartedEvent)
    async def bot_started(event: hikari.StartedEvent):

        Bot.start_time = time.time()

        if os.environ.get('DSP') == "Production":
            logging.info("███ Bot is in the production environment")
            await client.clear_application_commands()
            await client.declare_global_commands()
        else:
            logging.info("███ Bot is in a testing environment")
            await bot.rest.edit_my_member(guild=TESTING_GUILD_ID, nickname=f"Pela ({os.environ.get('DSP')})")
            await client.declare_global_commands(guild=TESTING_GUILD_ID)


        # for c in client.components:
        #     for command in c.slash_commands:
        #         print(command.name + " " + str(command.tracked_command_id))
        # declared_commands = await client.declare_global_commands()

    #     for command in declared_commands:
    #         print("declared " + command.name)
    # #
    # @bot.listen(hikari.GuildAvailableEvent)
    # async def guild_available(event: hikari.GuildAvailableEvent):
    #     guild_id = event.guild_id
    #     pass
    #     # await client.declare_global_commands(command_ids=None, guild=guild_id, force=True)
    #     # await client.declare_global_commands([], guild=guild_id, force=True)

    return bot
