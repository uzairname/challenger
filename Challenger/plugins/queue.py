import asyncio

import tanjun
from datetime import datetime

import pandas as pd

from Challenger.utils import *
from Challenger.database import Session
from Challenger.config import *


component = tanjun.Component(name="queue module")

#join the queue
@component.with_slash_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.as_slash_command("join", "join the queue", default_to_ephemeral=True, always_defer=True)
@ensure_registered
@get_channel_lobby
async def join_q(ctx: tanjun.abc.Context, lobby:pd.Series, client:tanjun.Client=tanjun.injected(type=tanjun.Client)) -> None:

    await ctx.respond("please wait")

    DB = Session(ctx.guild_id)

    #Ensure player has at the required role
    if lobby["required_role"]:
        if not lobby["required_role"] in ctx.member.role_ids:
            await ctx.respond(f"{ctx.author.mention} You're missing the required role to join this lobby")
            return

    player_id=ctx.author.id

    #Ensure player isn't already in queue
    if lobby["player"] == player_id:
        await ctx.respond(f"{ctx.author.mention} you're already in the queue")
        return

    #Ensure player declared last match
    matches = DB.get_matches(user_id=player_id)

    if not matches.empty:
        match = matches.iloc[0]
        if match["outcome"] is None:
            if match["p1_id"] == player_id and match["p1_declared"] is None or match["p2_id"] == player_id and match["p2_declared"] is None:
                await ctx.edit_initial_response("You need to /declare the results for match " + str(match.name))
                return

    #add player to queue
    if not lobby["player"]:

        asyncio.create_task(remove_after_timeout(ctx, DB), name=str(ctx.author.id) + str(lobby.name) + "_queue_timeout")
        print(str(ctx.author.id) + str(lobby.name) + "_queue_timeout")

        lobby["player"] = player_id
        DB.upsert_lobby(lobby)

        await ctx.edit_initial_response(f"You silently joined the queue")
        await ctx.get_channel().send("A player has joined the queue for **" + str(lobby["lobby_name"]) + "**")

    else:
        await ctx.edit_initial_response("You silently joined the queue")
        await ctx.get_channel().send("Queue is full. Creating match")

        p1_info = DB.get_players(user_id=lobby['player']).iloc[0]
        p2_info = DB.get_players(user_id=player_id).iloc[0]

        await remove_from_queue(ctx, DB, lobby)

        await start_new_match(ctx, p1_info, p2_info, client=client)


#leave queue
@component.with_slash_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.as_slash_command("leave", "leave the queue", default_to_ephemeral=True, always_defer=True)
@ensure_registered
@get_channel_lobby
async def leave_q(ctx: tanjun.abc.Context, lobby) -> None:

    DB = Session(ctx.guild_id)
    player_id = ctx.author.id

    if lobby["player"] == player_id:

        await remove_from_queue(ctx, DB, lobby)
        await ctx.edit_initial_response("Left the queue")

    else:
        await ctx.edit_initial_response("You're not in the queue")




def get_first_match_results(ctx:tanjun.abc.Context, DB, num_matches, player_id):
    matches = DB.get_matches(user_id=player_id, limit=num_matches)
    if matches.empty:
        return matches
    matches = matches.sort_values(by="match_id", ascending=True)
    return matches.iloc[:num_matches]


@component.with_slash_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.as_slash_command("queue", "queue status", default_to_ephemeral=True)
@get_channel_lobby
async def queue_status(ctx: tanjun.abc.Context, lobby) -> None:
    if lobby["player"]:
        await ctx.edit_initial_response("1 player in queue")
    else:
        await ctx.edit_initial_response("queue is empty")



queue = tanjun.Component(name="queue", strict=True).load_from_scope().make_loader()