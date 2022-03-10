import hikari
import tanjun

import logging
import os
from __init__ import *


def build_bot() -> hikari.GatewayBot:
    TOKEN = os.environ.get("PELA_TOKEN")
    bot = hikari.GatewayBot(TOKEN)

    client = (
        tanjun.Client.from_gateway_bot(
            bot,
            mention_prefix=True
        )
    )

    client.load_modules("plugins.util")

    @bot.listen(hikari.StartedEvent)
    async def bot_started(event: hikari.StartedEvent):
        if os.environ.get('DSP') == "Production":
            logging.info("███ Bot is in the production environment")
            return
        await bot.rest.edit_my_member(guild=GUILD_ID, nickname=f"Pela ({os.environ.get('DSP')})")
        logging.info("███ Bot is in a testing environment")


    @bot.listen(hikari.GuildAvailableEvent)
    async def guild_available(event: hikari.GuildAvailableEvent):
        guild_id = event.guild_id
        await client.declare_global_commands(None, guild=guild_id, force=True)
        await client.declare_application_commands([], guild=guild_id, force=True)



    return bot
