from plugins.utils import *
from __main__ import DB
import asyncio
import math
from datetime import datetime
import time


component = tanjun.Component(name="player module")


@component.with_slash_command
@tanjun.as_slash_command("register", "Join the fun!", default_to_ephemeral=True)
async def register(ctx: tanjun.abc.Context) -> None:

    DB.open_connection(ctx.guild_id)
    user_id = ctx.author.id
    player_info = DB.get_players(user_id)

    if not player_info.empty:
        DB.update_player(user_id, username=ctx.author.username)
        await ctx.respond("You've already registered. Updated your info")
        DB.close_connection()
        return

    DB.add_player(user_id)
    DB.update_player(user_id, username=ctx.author.username, elo=DEFAULT_ELO, time_registered=datetime.fromtimestamp(time.time()))

    DB.close_connection()

    await ctx.respond("You have registered.")



@component.with_slash_command
@tanjun.as_slash_command("stats", "view your stats", default_to_ephemeral=False)
async def get_match(ctx: tanjun.abc.Context) -> None:
    player_id = ctx.author.id
    DB.open_connection()

    player_info = DB.get_players(player_id).iloc[0,:]

    response = "Stats for " + str(player_info["username"]) + ":\n" +\
        "elo: " + str(round(player_info["elo"]))

    await ctx.respond(response, delete_after=200)
    DB.close_connection()



def calculate_elo_change(player1, player2, new_result, old_result):
    elo_change = {"player1":None, "player2":None}


    #old result is usually 0.
    #calculate elo for old result, then subtract it.
    #calculate elo for new result, then add it.

    #player 1 lost and has -1.   they should win (loss should've given -3, win should've given +5). new elo is -1--3+5 = 7.




@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())