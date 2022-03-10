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
            mention_prefix=True,
            declare_global_commands=GUILD_ID
        )
    ).add_prefix("!")

    client.load_modules("plugins.util", "plugins.suggestions")

    @bot.listen(hikari.StartedEvent)
    async def bot_started(event: hikari.StartedEvent):
        if os.environ.get('DSP') == "Production":
            logging.info("███ Bot is in the production environment")
            return
        await bot.rest.edit_my_member(guild=907729885726933043, nickname=f"Pela ({os.environ.get('DSP')})")
        logging.info("███ Bot is in a testing environment")

    return bot

