from plugins.utils import *
from __main__ import DB
import asyncio
import math





component = tanjun.Component(name="queue module")

#join the queue (if new, register)
@component.with_slash_command
@tanjun.as_slash_command("join", "join the queue", default_to_ephemeral=True)
async def join_q(ctx: tanjun.abc.Context) -> None:

    #TODO
    # Update user's discord tag in DB
    # make sure user is registered before joining. If not, promt to use register command which should ask for name

    player_id = ctx.author.id
    DB.open_connection()

    #check if player is registered

    player_info = DB.get_players(user_id=player_id)
    if player_info.empty:
        await ctx.respond(f"hello {ctx.author.mention}. Please register with /register to play")
        DB.close_connection()
        return


    match = DB.get_matches().iloc[0, :]

    print("latest match:\n" + str(match))


    if match["player1"] == player_id or match["player2"] == player_id:
        response = await ctx.respond(f"{ctx.author.mention} you're already in the queue", ensure_result=True)
        await asyncio.sleep(6)
        await response.delete()
        return


    if match["player1"] and match["player2"]: #should be redundant
        DB.create_match()
        match = DB.get_matches().iloc[0, :]


    if not match["player1"]:
        DB.update_match(match_id=match["match_id"], player1=player_id)
    elif not match["player2"]:
        DB.update_match(match_id=match["match_id"], player2=player_id)
    else:
        response = await ctx.respond(f"{ctx.author.mention} Try joining again")

    response = await ctx.respond(f"{ctx.author.mention} you have silently joined the queue", ensure_result=True)

    match = DB.get_matches().iloc[0, :]
    if match["player1"] and match["player2"]:
        channel = ctx.get_channel()
        await ctx.get_channel().send("Match " + str(match["match_id"]) + " started: " + str(match["player1"]) + " vs " + str(match['player2']))
    else:
        await ctx.get_channel().send("A player has joined match " + str(match["match_id"]))

    DB.close_connection()

    await asyncio.sleep(6)
    await response.delete()

    #catch errors here in case 3 people try to join at once


#leave queue
@component.with_slash_command
@tanjun.as_slash_command("leave", "leave the queue", default_to_ephemeral=True)
@check_errors
async def leave_q(ctx: tanjun.abc.Context) -> None:
    raise NotImplementedError
    await ctx.respond(f"{ctx.author.mention}. ")


# results={"won":["won", "win", "w"], "lost":["lost", "lose", "l"], "cancel":"cancel"}
class results:
    WIN = "won"
    LOSE = "lost"
    CANCEL = "cancelled"
@component.with_slash_command
@tanjun.with_str_slash_option("match_number", "optional, defaults to your latest match", default="latest")
@tanjun.with_str_slash_option("result", "result", choices={"won":results.WIN, "lost":results.LOSE, "cancel":results.CANCEL})
@tanjun.as_slash_command("declare", "declare a match's results", default_to_ephemeral=True)
async def declare_match(ctx: tanjun.abc.SlashContext, result, match_number) -> None:

    response = "sucessful"
    DB.open_connection()

    #check if staff is calling command.
    #If so,
    #   update results
    #If not,
    #   make sure player played in that match
    #   make sure match is full
    #   get match id, old declared_by, and desired result

    isStaff = False
    if isStaff:
        DB.update_match(match_id=match_number, declared_by="Staff")
        response = "Staff declared winner"

    try:
        def refresh():
            if match_number == "latest":
                return DB.get_matches(player=ctx.author.id).iloc[0,:]
            else:
                return DB.get_matches(player=ctx.author.id, match_id=match_number).iloc[0,:]
        match = refresh()
        print("█MATCH: \n" + str(match))
    except:
        await ctx.respond("No match found")
        DB.close_connection()
        return


    #check if match is full
    if match["player1"] is None or match["player2"] is None:
        await ctx.respond("This match's queue isn't full")
        DB.close_connection()
        return

    #set the new declared_by and outcome
    #get match id, previous declared_by, and desired result
    match_id=match["match_id"]

    #set the new declared_by and outcome

    if match["player1"] == ctx.author.id:
        cur_player = "player1"
        opponent = "player2"
        if result == results.WIN:
            DB.update_match(match_id=match_id, p1_declared=cur_player)
        elif result == results.LOSE:
            DB.update_match(match_id=match_id, p1_declared=opponent)
        if result == results.CANCEL:
            DB.update_match(match_id=match_id, p1_declared=results.CANCEL)
    else:
        cur_player = "player2"
        opponent = "player1"
        if result == results.WIN:
            DB.update_match(match_id=match_id, p2_declared=cur_player)
        elif result == results.LOSE:
            DB.update_match(match_id=match_id, p2_declared=opponent)
        if result == results.CANCEL:
            DB.update_match(match_id=match_id, p2_declared=results.CANCEL)

    response = "Declared results for match " + str(match_id)

    match = refresh()

    old_outcome = match["outcome"]

    if match["p1_declared"] and match["p2_declared"]:
        if match["p1_declared"] == match["p2_declared"]:
            new_outcome = match["p1_declared"]
            if old_outcome != new_outcome:
                await ctx.get_channel().send("Match " + str(match_id) + " results: " + str(new_outcome))
                DB.update_match(match_id, outcome=new_outcome)
            else:
                response = "Match outcome is already " + str(new_outcome)

    DB.close_connection()
    await ctx.respond(response, ensure_result=True)






#TODO commands:
# when voting result: best of 1, 3, or 5
# get my recent matches
# display leaderboard
# dispute old match by match id
# get my stats - wins, losses, elo
# -
# staff commands:
# change old match (update both player's elo)

#TODO other notes:
# Elo with a small scale factor, and relatively large K value to minimize grinding. approx. 5 games to stabilize elo at skill level
#change of less than 1 elo is dispayed as '<1" instead of 0
# displayed elo change is given as rounded. going from 6.7(7) to 5.4(5) is not 6.7-5.4(1), but 7-5(2)

@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())