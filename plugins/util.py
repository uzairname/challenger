import hikari

from plugins.utils import *
from __init__ import *
from __main__ import PelaBot
import time



component = tanjun.Component(name="hi module")

@component.with_slash_command
@tanjun.as_slash_command("help", "About", default_to_ephemeral=True)
async def hi_test(ctx: tanjun.abc.Context, bot:PelaBot=tanjun.injected(type=PelaBot)) -> None:

    embed = hikari.Embed(title="About", description="This is the testing version. More features coming soon")

    embed.set_footer("Lilapela#1234")

    embed.add_field(name="Game commands", value="""
    /register - register or update your name
    /join - join the queue. You must be in a valid channel
    /leave - leave q
    /queue - see whether queue is empty
    /declare [win, loss, draw] declare the results of your match. Both players must declare for match to be decided
    /match - view the results of your latest match
    /lb - view the leaderboard
    /stats - see your elo
    
    """)
    embed.add_field(name="Staff commands", value="""
    /configure ...
    \t[lobby] - Add or change lobbies
    \t[results] - Set the channel for match results announcements
    /reset - completely resets all match and player data for your server
    """)

    embed.add_field(name="Other commands", value="""
    /invite-pela Get the invite link for the bot
    /uptime See how long since the bot's last reset
    """)

    await ctx.respond(f"Hi {ctx.author.mention}!!", embeds=[embed], user_mentions=True)


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