import hikari
import tanjun

import os


def build_bot() -> hikari.GatewayBot:
    TOKEN = os.environ.get("DISCORD_TOKEN")
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