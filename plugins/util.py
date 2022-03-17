import asyncio

from plugins.utils import *
from __init__ import *

from bot import PelaBot
import time

nl = "\n"

component = tanjun.Component(name="hi module")


@component.with_slash_command
@tanjun.with_str_slash_option("guild", "a")
@tanjun.as_slash_command("open", "test, delete", default_to_ephemeral=True)
async def open_test(ctx: tanjun.abc.Context, guild) -> None:
    DB.open_connection(guild_id=guild)
    await ctx.respond("done")


@component.with_slash_command
@tanjun.as_slash_command("get", "test, delete", default_to_ephemeral=True)
async def get_test(ctx: tanjun.abc.Context) -> None:
    DB.get_recent_matches()
    await ctx.respond("done")


@component.with_slash_command
@tanjun.as_slash_command("hi", "a", default_to_ephemeral=True)
async def hi_test(ctx: tanjun.abc.Context) -> None:
    await asyncio.sleep(6)
    response = await ctx.respond(f"Hi {ctx.author.mention}!{nl}This is the testing version. More features coming soon", ensure_result=True)
    await asyncio.sleep(6)
    await response.delete()


@component.with_slash_command
@tanjun.as_slash_command("invite-pela", "invite pela to your own server", default_to_ephemeral=False)
async def hi_test(ctx: tanjun.abc.Context) -> None:
    await ctx.respond(f"This is the invite link: " + INVITE_LINK)


@component.with_slash_command
@tanjun.as_slash_command("uptime", "get Pela's uptime", default_to_ephemeral=False)
async def uptime(ctx:tanjun.abc.Context) -> None:
    time_diff = time.time() - PelaBot.start_time
    await ctx.respond("Pela's current session's uptime is: " + str(round(time_diff/3600)) + " hours, " + str(round((time_diff/60)%60)) + " minutes, " + str(round(time_diff%60)) + " seconds")


@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())