import asyncio

import hikari
import tanjun
from datetime import datetime

import pandas as pd

from Challenger.utils import *
from Challenger.database import Guild_DB
from Challenger.config import *


component = tanjun.Component(name="queue module")

#join the queue
@component.with_slash_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.as_slash_command("join", "join the queue", default_to_ephemeral=True, always_defer=True)
@ensure_registered
@get_channel_lobby
async def join_q(ctx: tanjun.abc.Context, lobby:pd.Series, client:tanjun.Client=tanjun.injected(type=tanjun.Client)) -> None:

    response = await ctx.respond("please wait", ensure_result=True)

    DB = Guild_DB(ctx.guild_id)

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
                embed = hikari.Embed(title="You have an ongoing match", description="/declare the results or ask staff to set finalize the match (type /match-history for more details)", color=Colors.ERROR)
                await ctx.edit_initial_response(embed=embed)
                return

    #add player to queue
    if not lobby["player"]:

        asyncio.create_task(remove_from_q_timeout(ctx, DB), name=str(ctx.author.id) + str(lobby.name) + "_queue_timeout")

        lobby["player"] = player_id
        DB.upsert_lobby(lobby)

        await ctx.edit_initial_response(f"You silently joined the queue")
        await ctx.get_channel().send("A player has joined the queue")

    else:
        await ctx.edit_initial_response("You silently joined the queue")
        await ctx.get_channel().send("Queue is full. Creating match")

        p1_info = DB.get_players(user_id=lobby['player']).iloc[0]
        p2_info = DB.get_players(user_id=player_id).iloc[0]

        await remove_from_queue(DB, lobby)

        await start_announce_new_match(ctx, p1_info, p2_info)


async def start_announce_new_match(ctx:tanjun.abc.Context, p1_info, p2_info):
    """creates a new match between the 2 players and announces it to the channel"""

    DB = Guild_DB(ctx.guild_id)

    p1_ping = "<@" + str(p1_info.name) + ">"
    p2_ping = "<@" + str(p2_info.name) + ">"

    p1_is_ranked = p1_info["is_ranked"]
    p2_is_ranked = p2_info["is_ranked"]

    new_match = DB.get_new_match()

    new_match[["time_started", "p1_id", "p2_id", "p1_elo", "p2_elo", "p1_is_ranked", "p2_is_ranked"]] = \
        [datetime.now(), p1_info.name, p2_info.name, p1_info["elo"], p2_info["elo"], p1_is_ranked, p2_is_ranked]

    DB.upsert_match(new_match)

    embed = Custom_Embed(type=Embed_Type.INFO, title="Match " + str(new_match.name) + " started", description=p1_info["tag"] + " vs " + p2_info["tag"])

    await ctx.get_channel().send(content=p1_ping+ " " + p2_ping, embed=embed, user_mentions=True)


#leave queue
@component.with_slash_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.as_slash_command("leave", "leave the queue", default_to_ephemeral=True, always_defer=True)
@ensure_registered
@get_channel_lobby
async def leave_q(ctx: tanjun.abc.Context, lobby) -> None:

    DB = Guild_DB(ctx.guild_id)
    player_id = ctx.author.id

    if lobby["player"] == player_id:
        await remove_from_queue(DB, lobby)
        await ctx.edit_initial_response("Left the queue")
        await ctx.get_channel().send("A player has left the queue")
    else:
        await ctx.edit_initial_response("You're not in the queue")


@component.with_slash_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.as_slash_command("queue", "queue status", default_to_ephemeral=True)
@get_channel_lobby
async def queue_status(ctx: tanjun.abc.Context, lobby) -> None:
    if lobby["player"]:
        await ctx.edit_initial_response("1 player in queue")
    else:
        await ctx.edit_initial_response("Queue is empty")



queue = tanjun.Component(name="queue", strict=True).load_from_scope().make_loader()