import hikari
from utils.utils import *
from utils.ELO import *
from database import Database
from __main__ import bot


component = tanjun.Component(name="queue module")


async def start_new_match(ctx:tanjun.abc.Context, p1_info, p2_info):
    DB = Database(ctx.guild_id)

    p1_ping = "<@" + str(p1_info["user_id"]) + ">"
    p2_ping = "<@" + str(p2_info["user_id"]) + ">"

    new_match = DB.get_new_match()
    new_match[["p1_id", "p2_id", "p1_elo", "p2_elo", "p1_is_ranked", "p2_is_ranked"]] = \
        [p1_info["user_id"], p2_info["user_id"], p1_info["elo"], p2_info["elo"], p1_info["is_ranked"], p2_info["is_ranked"]]

    DB.upsert_match(new_match)

    await ctx.get_channel().send("Match " + str(new_match.name) + " started: " + p1_ping + " vs " + p2_ping, user_mentions=True)



async def update_match(matches, match_id, new_result = None, updated_players=None):
    updated_players = updated_players or []

    match = matches.loc[match_id]


#join the queue
@component.with_slash_command
@tanjun.as_slash_command("join", "join the queue", default_to_ephemeral=True, always_defer=True)
@ensure_registered
@check_for_queue
async def join_q(ctx: tanjun.abc.Context, queue) -> None:

    DB = Database(ctx.guild_id)

    #Ensure player has at least 1 role in the queue roles
    is_allowed = False
    for role in queue["roles"]:
        if role in ctx.member.role_ids:
            is_allowed = True
    if not is_allowed:
        await ctx.respond(f"{ctx.author.mention} You're missing the required roles to join this lobby")
        return

    player_id=ctx.author.id

    #Ensure player isn't already in queue
    if queue["player"] == player_id:
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
    if not queue["player"]:
        queue["player"] = player_id
        DB.upsert_queue(queue)

        await ctx.edit_initial_response(f"You silently joined the queue")
        await ctx.get_channel().send("A player has joined the queue for **" + str(queue["lobby_name"]) + "**")
    else:
        await ctx.edit_initial_response("Queue is full. Creating match")

        p1_info = DB.get_players(user_id=queue['player']).iloc[0]
        p2_info = DB.get_players(user_id=player_id).iloc[0]

        queue["player"] = None
        DB.upsert_queue(queue)

        await start_new_match(ctx, queue, p1_info, p2_info)


#leave queue
@component.with_slash_command
@tanjun.as_slash_command("leave", "leave the queue", default_to_ephemeral=True, always_defer=True)
@ensure_registered
@check_for_queue
async def leave_q(ctx: tanjun.abc.Context, queue) -> None:

    DB = Database(ctx.guild_id)
    player_id = ctx.author.id

    response = "Left the queue"
    if queue["player"] == player_id:
        queue["player"] = None
        await ctx.get_channel().send("A player has left the queue")
    else:
        response = "You're not in the queue"

    DB.upsert_queue(queue)
    await ctx.edit_initial_response(response)



def get_first_match_results(ctx:tanjun.abc.Context, DB, num_matches, player_id):
    matches = DB.get_matches(user_id=player_id, number=num_matches)
    if matches.empty:
        return matches
    matches = matches.sort_values(by="match_id", ascending=True)
    return matches.iloc[:num_matches]


@component.with_slash_command
@tanjun.as_slash_command("queue", "queue status", default_to_ephemeral=False)
@check_for_queue
async def queue_status(ctx: tanjun.abc.Context, queue) -> None:
    if queue["player"]:
        await ctx.edit_initial_response("1 player in queue")
    else:
        await ctx.edit_initial_response("queue is empty")




@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())