import hikari

from plugins.utils import *
from __init__ import *
from __main__ import PelaBot
import time



component = tanjun.Component(name="hi module")

@component.with_slash_command
@tanjun.as_slash_command("hi", "a", default_to_ephemeral=True)
async def hi_test(ctx: tanjun.abc.Context, bot:PelaBot=tanjun.injected(type=PelaBot)) -> None:

    print((bot.cache.get_guild_channel(953690285035098142)).permission_overwrites)

    response = await ctx.respond(f"Hi {ctx.author.mention}!\nThis is the testing version. More features coming soon", ensure_result=True)


@component.with_slash_command
@tanjun.as_slash_command("invite-pela", "invite pela to your own server", default_to_ephemeral=False)
async def hi_test(ctx: tanjun.abc.Context) -> None:
    await ctx.respond(f"This is the invite link: " + INVITE_LINK)


@component.with_slash_command
@tanjun.as_slash_command("uptime", "get Pela's uptime", default_to_ephemeral=False)
async def uptime(ctx:tanjun.abc.Context, bot:PelaBot=tanjun.injected(type=PelaBot)) -> None:
    time_diff = time.time() - bot.start_time
    await ctx.respond("Pela's current session's uptime is: " + str(round(time_diff/3600)) + " hours, " + str(round((time_diff/60)%60)) + " minutes, " + str(round(time_diff%60)) + " seconds")


@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())