from plugins.utils import *
from __main__ import DB
import asyncio
import math


class results:
    WIN = "won"
    LOSE = "lost"
    CANCEL = "cancelled"
    PLAYER1 = "player 1"
    PLAYER2 = "player 2"

#=======================================================

component = tanjun.Component(name="queue module")

#join the queue (if new, register)
@component.with_slash_command
@tanjun.as_slash_command("join", "join the queue", default_to_ephemeral=True)
async def join_q(ctx: tanjun.abc.Context) -> None:

    player_id = ctx.author.id
    DB.open_connection()

    #check if player is registered
    player_info = DB.get_players(user_id=player_id)
    if player_info.empty:
        await ctx.respond(f"hello {ctx.author.mention}. Please register with /register to play")
        DB.close_connection()
        return

    match = DB.get_matches().iloc[0, :]

    #assuming latest match shoud never have 2 ppl, this should never happen
    if match["player1"] and match["player2"]:
        await ctx.get_channel().send("Match was full, creating new match")
        DB.create_match()
        match = DB.get_matches().iloc[0, :]

    #check whether player is in the latest match
    if match["player1"] == player_id or match["player2"] == player_id:
        response = await ctx.respond(f"{ctx.author.mention} you're already in the queue", ensure_result=True)
        DB.close_connection()
        return

    if not match["player1"]:
        DB.update_match(match_id=match["match_id"], player1=player_id)
    elif not match["player2"]:
        DB.update_match(match_id=match["match_id"], player2=player_id)
    else:
        response = f"{ctx.author.mention} Try joining again"

    response = f"{ctx.author.mention} you have silently joined the queue"

    match = DB.get_matches().iloc[0,:]

    if match["player1"] and match["player2"]: #After adding the player, check if match is full
        channel = ctx.get_channel()
        await ctx.get_channel().send("Match " + str(match["match_id"]) + " started: "\
                                     + str(match["player1"]) + " vs " + str(match['player2']))
        DB.create_match()
    else:
        await ctx.get_channel().send("A player has joined match " + str(match["match_id"]))

    DB.close_connection()

    await ctx.respond(response, ensure_result=True, delete_after=5)


#leave queue
@component.with_slash_command
@tanjun.as_slash_command("leave", "leave the queue", default_to_ephemeral=True)
async def leave_q(ctx: tanjun.abc.Context) -> None:

    player_id = ctx.author.id
    DB.open_connection()

    # check if player is registered
    player_info = DB.get_players(user_id=player_id)
    if player_info.empty:
        await ctx.respond(f"hello {ctx.author.mention}. Please register with /register to play")
        DB.close_connection()
        return

    match = DB.get_matches().iloc[0,:]

    response = "You've left the queue"
    if match["player1"] and match["player2"]:
        response = "Queue is already full, match should've started" # assuming latest match never has 2 ppl, this should never happen
        DB.close_connection()
        return
    if match["player1"] == player_id:
        DB.update_match(match["match_id"], player1 = None)
        await ctx.get_channel().send("A player has left match " + str(match["match_id"]))
    elif match["player2"] == player_id:  #Assuming player1 can't leave the match after player2 joins, this should never happen
        DB.update_match(match["match_id"], player2 = None)
        await ctx.get_channel().send("player 2 left " + str(match["match_id"]))
    else:
        response = f"You're not queued for the next match"

    DB.close_connection()

    await ctx.respond(response)


@component.with_slash_command
@tanjun.with_str_slash_option("match_number", "optional, defaults to your latest match", default="latest")
@tanjun.with_str_slash_option("result", "result", choices={"won":results.WIN, "lost":results.LOSE, "cancel":results.CANCEL, "player 1":results.PLAYER1, "player 2":results.PLAYER2})
@tanjun.as_slash_command("declare", "declare a match's results", default_to_ephemeral=True)
async def declare_match(ctx: tanjun.abc.SlashContext, result, match_number) -> None:

    DB.open_connection()

    player_info = DB.get_players(user_id=ctx.author.id)
    print("player info:\n" + str(player_info))
    print("\n" + str(player_info["role"]))

    isStaff = False

    print("staff : " + str(isStaff))

    try:
        def get_match():
            if isStaff:
                return DB.get_matches(match_id=match_number) #don't filter by player if staff
            elif match_number == "latest": #they didn't specify a match number
                return DB.get_matches(player=ctx.author.id).iloc[0,:]
            else:
                return DB.get_matches(player=ctx.author.id, match_id=match_number).iloc[0,:]
        match = get_match()
        match_id = match["match_id"]
        print("█MATCH: \n" + str(match))
    except:
        print("error in getting match")
        await ctx.respond("No match found")
        DB.close_connection()
        return

    #check if match is full
    if match["player1"] is None or match["player2"] is None:
        await ctx.respond("This match's queue isn't full")
        DB.close_connection()
        return

    #set the new declared_by and outcome
    #set the new declared_by and outcome

    desired_outcome=None
    if match["player1"] == ctx.author.id:
        cur_player = results.PLAYER1
        opponent = results.PLAYER2
        if result == results.WIN:
            desired_outcome=cur_player
        elif result == results.LOSE:
            desired_outcome=opponent
        elif result == results.CANCEL:
            desired_outcome=results.CANCEL
        DB.update_match(match_id=match_id, p1_declared=desired_outcome)
    elif match["player2"] == ctx.author.id:
        cur_player = results.PLAYER2
        opponent = results.PLAYER1
        if result == results.WIN:
            desired_outcome=cur_player
        elif result == results.LOSE:
            desired_outcome=opponent
        elif result == results.CANCEL:
            desired_outcome=results.CANCEL
        DB.update_match(match_id=match_id, p2_declared=desired_outcome)
    elif isStaff:
        desired_outcome=result
        DB.update_match(match_id=match_id, outcome=result)

    old_outcome = match["outcome"]
    match = get_match()

    response = "Declared results for match " + str(match_id)

    if old_outcome != desired_outcome:
        if isStaff:
            await ctx.get_channel().send("Match " + str(match_id) + " results declared by staff: " + str(desired_outcome))
            DB.update_match(match_id, outcome=desired_outcome)
        elif match["p1_declared"] == match["p2_declared"]:
            await ctx.get_channel().send("Match " + str(match_id) + " results: " + str(desired_outcome))
            DB.update_match(match_id, outcome=desired_outcome)
    else:
        response = "Match outcome is already " + str(desired_outcome)

    DB.close_connection()
    await ctx.respond(response)






@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())