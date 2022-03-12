import math

import hikari
import tanjun.abc

from plugins.utils import *
from __main__ import DB
import asyncio


DEFAULT_ELO = 50 #everyone's starting score
DEFAULT_K = 12  # maximum change in one game
DEFAULT_SCALE = 30  # elo difference approximating 10x skill difference

def calc_elo_change(winner_elo, loser_elo): #winner's elo change. It's negative equals loser's elo change
    diff = winner_elo - loser_elo
    k = DEFAULT_K
    scale = DEFAULT_SCALE
    def expected_score(A, B):  # A's expected probability of winning
        return 1 / (1 + math.pow(10, -(A - B) / scale))
    elo = k * expected_score(loser_elo, winner_elo)  # elo the winner gains
    return elo



component = tanjun.Component(name="queue module")


#join the queue (if new, register)
@component.with_slash_command
@tanjun.as_slash_command("join", "join the queue", default_to_ephemeral=False)
async def join_q(ctx: tanjun.abc.Context) -> None:
    player_id = ctx.author.id
    DB.open_connection()
    match = DB.get_recent_matches().iloc[0,:]
    # refresh
    # return if player is already in latest match
    # add player to first available slot, give warning if there are none
    # refresh
    # check if most recent match is full
    # if so, announce 1v1 and make a new match
    # if not, announce player joined

    print("latest match:\n" + str(match))

    if match["player1"] and match["player2"]: #should be redundant
        DB.create_match()
        match = DB.get_recent_matches().iloc[0,:]

    if match["player1"] == player_id or match["player2"] == player_id:
        response = await ctx.respond(f"{ctx.author.mention} you're already in the queue", ensure_result=True)
        await asyncio.sleep(6)
        await response.delete()
        return

    if not match["player1"]:
        DB.update_match(match_id=match["match_id"], player1=player_id)
    elif not match["player2"]:
        DB.update_match(match_id=match["match_id"], player2=player_id)
    else:
        response = await ctx.respond(f"{ctx.author.mention} Try joining again")

    response = await ctx.respond(f"{ctx.author.mention} you have silently joined the queue", ensure_result=True)

    match = DB.get_recent_matches().iloc[0,:]
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
    await ctx.respond(f"{ctx.author.mention} you have silently left the queue")
    await ctx.get_channel().send("A player has left match 1")


results={"won":["won", "win", "w"], "lost":["lost", "lose", "l"], "cancel":"cancel"}
# declare the match results, or update them. When declaring for the first time, the match will have no "result" or "elo change"
# when editing, the elo change will either be reversed or made 0 if cancelled
@component.with_slash_command
@tanjun.with_str_slash_option("best_of", "optional, defaults to 1", choices=["1","3","5"], default="1")
@tanjun.with_str_slash_option("match_number", "optional, defaults to your latest match", default="latest")
@tanjun.with_str_slash_option("result", "result", choices={"won":"won", "lost":"lost", "cancel":"cancel"})
@tanjun.as_slash_command("declare", "declare a match's results", default_to_ephemeral=True)
async def declare_match(ctx: tanjun.abc.SlashContext, result, match_number, best_of) -> None:

    DB.open_connection()

    response = await ctx.respond(f" you're already in the queue", ensure_result=True)
    a = ctx.author.id
    await asyncio.sleep(1)
    await response.delete()
    return

    #check if staff is calling command.
    #If so,
    #   update results
    #If not,
    #   make sure player played in that match
    #   make sure match is full
    #   get match id, old declared_by, and desired result
    #

    isStaff = False
    if isStaff:
        DB.update_match(match_id=match_number, declared_by="Staff")
        await ctx.respond("Staff declared winner")


    try:
        if match_number == "latest":
            match = DB.get_recent_matches(player=ctx.author.id).iloc[0,:]
        else:
            match = DB.get_recent_matches(player=ctx.author.id, match_id=match_number).iloc[0,:]
    except:
        await ctx.respond("No match found")
        DB.close_connection()
        return

    print(ctx.author.id)
    print("match info: " + str(match))

    #check if match is full
    if not match["player1"] and match["player2"]:
        await ctx.respond("This match's queue isn't full")
        DB.close_connection()
        return


    #set the new declared_by and outcome
    #get match id, previous declared_by, and desired result
    match_id=match["match_id"]
    declared_by=match["declared_by"]
    if str.lower(result) in results["won"]:
        declared_result = "won"
    elif str.lower(result) in results["lost"]:
        declared_result = "lost"
    elif str.lower(result) in results["cancel"]:
        declared_result = "cancel"
    else:
        await ctx.respond("invalid result")
        DB.close_connection()
        return

    #set the new declared_by and outcome

    notif = ""

    async def update_outcome():
        outcome = None

        if match["player1"] == ctx.author.id:
            cur_player = "1"
            opponent = "2"
        else:
            cur_player = "2"
            opponent = "1"

        if declared_result == "won":
            if declared_by==cur_player:
                await ctx.respond("You already declared a result")
                pass
            elif declared_by==opponent:
                pass
            else:
                pass
        elif declared_result == "lost":
            if declared_by == cur_player:
                await ctx.respond("You already declared a result")
            elif declared_by == opponent:
                DB.update_match(match_id=match_id, declared_by=cur_player)
                outcome=cur_player
            else:
                DB.update_match(match_id=match_id, declared_by=cur_player)
                outcome=cur_player
        if result==results["cancel"]:
            if declared_by == cur_player:
                await ctx.respond("You already declared a result")
            elif declared_by == opponent:
                DB.update_match()
                outcome="0"
            else:
                DB.update_match(match_id=match_id, declared_by=cur_player)

        DB.close_connection()
        return outcome

    new_outcome = await update_outcome()

    #Check if outcome is new
    if not new_outcome: #no new outcome decided
        await ctx.get_channel().send(f"{ctx.author.mention} declared " + str(declared_result))
        return

    if new_outcome==match["outcome"]: #previous outcome equals the new outcome
        await ctx.get_channel().send("Outcome already decided")
        return
    else:
        await ctx.get_channel().send("Match " + str(match_id) + " results: " + str(new_outcome))


    #check if player is registered, if not, register and send message
    # p1 voted win, p2 voted lose, (now decidedby p2). p2 votes lose again.
    #check what current state is could be:
    #   player1,  prev result was nothing
    #   Declares win:
    #       If decided_by player: Error you already voted
    #       If decided_by opp(assuming loss): Nothing (win conflict, or opp lost and alr decided)
    #       If decided_by no one: decided_by player
    #   Declares lose:
    #       If decided_by player: Error you already voted
    #       If decided_by opp(assuming loss): decided_by player           Update result: player2
    #       If decided_by no one: decided_by player.                      Update result: player2
    #   Declares cancel:
    #       Opponent has 10 mins to agree to cancel
    #       If decided_by no one: decided_by player Update result: cancel
    #
    #
    #
    #   Check if result is diff from prev result
    #   Old outcome nothing
    #       new outcome player:     wait for opp
    #       new outcome opp:        add and announce new outcome opp
    #   old outcome player:
    #       new outcome player:     Nothing
    #       new outcome opp:        are you sure?
    #   old outcome opp
    #       new outcome opp:        Nothing
    #       new outcome player:     already decided, Conflict



    #   Declares win:
    #        If decided_by winner: decided_by winner, ask a staff. ONLY IF other declarer is themself is other
    #        If decided_by loser: declared_by winner. update result.
    #        If decided_by no one: decided_by winner
    #   Declares lose:
    #        If decided_by loser, decided_by loser. update result, and notify warning ONLY IF other declarer is other
    #        If decided_by winner, decided_by loser. update result
    #        If decided_by no one, decided_by loser. update result
    #   Staff declares:
    #        If decided_by winner/loser, update result
    #        If decided_by staff, decided_by staff, ask higher staff




    # based on win or lose, update elo, and elo_change



#leave


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