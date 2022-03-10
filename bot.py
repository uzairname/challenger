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
        )
    )
    client.load_modules("plugins.util", "plugins.suggestions")#, "plugins.embeds")

    @bot.listen(hikari.StartedEvent)
    async def bot_started(event: hikari.StartedEvent):
        if os.environ.get('DSP') == "Production":
            logging.info("███ Bot is in the production environment")
        else:
            logging.info("███ Bot is in a testing environment")
            await bot.rest.edit_my_member(guild=GUILD_ID_PELA, nickname=f"Pela ({os.environ.get('DSP')})")

        for c in client.components:
            print(c.name)

        await client.declare_global_commands(guild=GUILD_ID_PELA)

    @bot.listen(hikari.GuildAvailableEvent)
    async def guild_available(event: hikari.GuildAvailableEvent):
        guild_id = event.guild_id
        pass
        # await client.declare_global_commands(command_ids=None, guild=guild_id, force=True)
        # await client.declare_global_commands([], guild=guild_id, force=True)

    return bot
