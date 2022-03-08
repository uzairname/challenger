import hikari
import tanjun
import os

from termcolor import colored

def build_bot() -> GatewayBot:
    TOKEN = os.environ.get("DISCORD_TOKEN")
    bot = hikari.GatewayBot(TOKEN)

    make_client(bot)

    return bot


def make_client(bot: hikari.GatewayBot) -> tanjun.Client:
    client = (
        tanjun.Client.from_gateway_bot(
            bot,
            mention_prefix=True,
            set_global_commands=GUILD_ID
        )
    ).add_prefix("!")

    print(colored('PELA: ', 'red') + "Log test")

    return client

