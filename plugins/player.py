import pandas as pd

from plugins.utils import *
from database import Database
from datetime import datetime
import time


component = tanjun.Component(name="player module")


async def ensure_registered(ctx: tanjun.abc.Context, DB:Database):
    player_info = DB.get_players(user_id=ctx.author.id)
    if player_info.empty:
        await ctx.respond(f"hello {ctx.author.mention}. Please register with /register to play", user_mentions=True)
        return None
    return player_info


@component.with_slash_command
@tanjun.as_slash_command("register", "Join the fun!", default_to_ephemeral=True)
async def register(ctx: tanjun.abc.Context) -> None:

    await ctx.edit_initial_response("...")

    DB = Database(ctx.guild_id)
    player_id = ctx.author.id
    players = DB.get_players(user_id=player_id)

    if ctx.member.nickname is not None:
        name = ctx.member.nickname
    else:
        name = ctx.author.username

    if players.empty:
        player = DB.get_new_player(ctx.author.id)
        player["username"] = name
        player["tag"] = ctx.author.username+ctx.author.discriminator
        player["time_registered"] = datetime.now()
        player["elo"] = DEFAULT_ELO
        DB.upsert_player(player)
        await ctx.get_channel().send(f"{ctx.author.mention} has registered!", user_mentions=True)
        return

    player = players.iloc[0]
    player["username"] = name
    player["tag"] = ctx.author.username + "#" + ctx.author.discriminator
    DB.upsert_player(player)
    await ctx.edit_initial_response("You've already registered. Updated your username")


@component.with_slash_command
@tanjun.with_str_slash_option("player", "their mention", default=None)
@tanjun.as_slash_command("stats", "view your stats", default_to_ephemeral=True)
async def get_stats(ctx: tanjun.abc.Context, player) -> None: #TODO show winrate

    await ctx.respond("...")

    DB = Database(ctx.guild_id)

    player_info = await ensure_registered(ctx, DB)
    if player_info is None:
        return
    player_info = player_info.iloc[0]

    if player:
        input_users = parse_input(str(player))["users"]
        if len(input_users) != 1:
            await ctx.edit_initial_response("Invalid player id")
            return
        players = DB.get_players(user_id=input_users[0])
        if players.empty:
            await ctx.edit_initial_response("Unknown or unregistered player")
            return
        player_info = players.iloc[0]

    response = "Stats for " + str(player_info["username"]) + ":\n" +\
        "elo: " + str(round(player_info["elo"]))

    await ctx.get_channel().send(response)



def calculate_elo_change(player1, player2, new_result, old_result):
    elo_change = {"player1":None, "player2":None}


    #old result is usually 0.
    #calculate elo for old result, then subtract it.
    #calculate elo for new result, then add it.

    #player 1 lost and has -1.   they should win (loss should've given -3, win should've given +5). new elo is -1--3+5 = 7.


@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())