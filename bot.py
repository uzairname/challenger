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

    client = (tanjun.Client.from_gateway_bot(bot))

    client.load_modules("plugins.util", "plugins.queue", "plugins.suggestions", "plugins.player")  #, "plugins.embeds")

    @bot.listen(hikari.StartedEvent)
    async def bot_started(event: hikari.StartedEvent):

        Bot.start_time = time.time()

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

    # async def guild_available(event: hikari.GuildAvailableEvent):
    #     guild_id = event.guild_id

    return bot