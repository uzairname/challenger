from plugins.utils import *
from __init__ import *

from bot import Bot
import time

nl = "\n"

component = tanjun.Component(name="hi module")


@component.with_slash_command
@tanjun.as_slash_command("hi", "a", default_to_ephemeral=False)
async def hi_test(ctx: tanjun.abc.Context) -> None:
    await ctx.respond(f"Hi {ctx.author.mention}!{nl}This is the testing version. More features coming soon")


@component.with_slash_command
@tanjun.as_slash_command("invite-pela", "invite pela to your own server", default_to_ephemeral=False)
async def hi_test(ctx: tanjun.abc.Context) -> None:
    await ctx.respond(f"This is the invite link: " + INVITE_LINK)


@component.with_slash_command
@tanjun.as_slash_command("uptime", "get Pela's uptime", default_to_ephemeral=False)
async def uptime(ctx:tanjun.abc.Context) -> None:
    time_diff = time.time() - Bot.start_time
    await ctx.respond("Pela's current session's uptime is: " + str(round(time_diff/60, 2)) + " minutes")


@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())