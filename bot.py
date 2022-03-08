import hikari
import os

from bcolors import bcolors

bot = hikari.GatewayBot(os.environ.get("DISCORD_TOKEN"))


@bot.listen()
async def ping(event: hikari.GuildMessageCreateEvent) -> None:
    if event.is_bot or not event.content:
        return
    if event.content.startswith("hi"):
        await event.message.respond("hello")

print(f"{bcolors.OKCYAN}PELA: " + "Log test")
bot.run()
