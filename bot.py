import hikari
import tanjun

import os


INVITE_LINK="https://discord.com/api/oauth2/authorize?client_id=908432840566374450&permissions=544857254992&scope=bot%20applications.commands"


def build_bot() -> hikari.GatewayBot:
    TOKEN = os.environ.get("PELA_TOKEN")
    bot = hikari.GatewayBot(TOKEN)

    client = (
        tanjun.Client.from_gateway_bot(
            bot,
            mention_prefix=True,
            declare_global_commands=True
        )
    ).add_prefix("!")

    client.load_modules("plugins.util", "plugins.embeds", "plugins.suggestions")

    @bot.listen(hikari.StartedEvent)
    async def bot_started(event: hikari.StartedEvent):
        await bot.rest.edit_my_member(guild=907729885726933043, nickname=f"Pela ({os.environ.get('DSP')})")

    return bot