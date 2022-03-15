import logging

from plugins.utils import *
from __main__ import DB


component = tanjun.Component(name="queue module")


#join the queue
@component.with_slash_command
@tanjun.as_slash_command("join", "join the queue", default_to_ephemeral=True)
async def join_q(ctx: tanjun.abc.Context) -> None:

    DB.open_connection()

    #Ensure player is registered
    player_id = ctx.author.id
    player_info = DB.get_players(user_id=player_id)
    if player_info.empty:
        await ctx.respond(f"hello {ctx.author.mention}. Please register with /register to play")
        DB.close_connection()
        return

    #get queue info
    match = DB.get_matches().iloc[0,:]
    #ensure queue isn't full
    if match["player1"] and match["player2"]: #assuming latest match shoud never have 2 ppl, this should never happen
        await ctx.get_channel().send("Match was full, creating new match")
        DB.create_match()
        match = DB.get_matches().iloc[0, :]

    #check whether player is already in the queue
    if match["player1"] == player_id or match["player2"] == player_id:
        await ctx.respond(f"{ctx.author.mention} you're already in the queue")
        DB.close_connection()
        return

    #add player to queue along with relevant info
    player_elo = DB.get_players(user_id=player_id).iloc[0,:]["elo"]
    if not match["player1"]:
        DB.update_match(match_id=match["match_id"], player1=player_id, p1_elo=player_elo)
    elif not match["player2"]:
        DB.update_match(match_id=match["match_id"], player2=player_id, p2_elo=player_elo)
    else:
        response = f"{ctx.author.mention} Try joining again" #idk

    response = f"{ctx.author.mention} you have silently joined the queue"

    # After adding the player, check if match is full
    match = DB.get_matches().iloc[0,:]
    if match["player1"] and match["player2"]:
        player1_name = DB.get_players(match['player1']).iloc[0,:]["username"]
        player2_name = DB.get_players(match['player2']).iloc[0,:]["username"]

        await ctx.get_channel().send("Match " + str(match["match_id"]) + " started: "\
                                     + player1_name + " vs " + player2_name)
        DB.create_match()
    else:
        await ctx.get_channel().send("A player has joined match " + str(match["match_id"]))

    DB.close_connection()

    await ctx.respond(response, ensure_result=True, delete_after=5)


#leave queue
@component.with_slash_command
@tanjun.as_slash_command("leave", "leave the queue", default_to_ephemeral=True)
async def leave_q(ctx: tanjun.abc.Context) -> None:

    DB.open_connection()

    #check if player is registered
    player_id = ctx.author.id
    player_info = DB.get_players(user_id=player_id)
    if player_info.empty:
        await ctx.respond(f"hello {ctx.author.mention}. Please register with /register to play")
        DB.close_connection()
        return

    match = DB.get_matches().iloc[0,:]

    response = "You've left the queue"
    if match["player1"] and match["player2"]:
        await ctx.respond("Queue is already full, match should've started") # assuming latest match never has 2 ppl, this should never happen
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
@tanjun.with_str_slash_option("result", "result", choices={"won":results.WIN, "lost":results.LOSE, "cancel":results.CANCEL})
@tanjun.as_slash_command("declare", "declare a match's results", default_to_ephemeral=True)
async def declare_match(ctx: tanjun.abc.SlashContext, result, match_number) -> None:

    DB.open_connection()
    player_id = ctx.author.id
    player_info = DB.get_players(user_id=player_id)

    print("player info:\n" + str(player_info))
    print("\n" + str(player_info["role"]))

    try:
        def get_selected_match():
            if match_number == "latest": #they didn't specify a match number
                return DB.get_matches(player=player_id).iloc[0,:] #TODO by default make sure match is full
            else:
                return DB.get_matches(player=player_id, match_id=match_number).iloc[0,:]

        match = get_selected_match() #the current match
        match_id = match["match_id"]
        print("█MATCH: \n" + str(match))
    except:
        print("error in getting match")
        await ctx.respond("No match found")
        DB.close_connection()
        return

    #check if match is full, won't be needed
    if match["player1"] is None or match["player2"] is None:
        await ctx.respond("Your match hasn't started")
        DB.close_connection()
        return

    async def update_players_elo(old_result, new_result):

        #note: changing the result of an old match has a cascading effect on all the subsequent players those players played against, and the players they played against, and so on... since your elo change depends on your and your opponent's prior elo. If the changed match is very old, the recursive algorithm might take a while

        p1_elo = match["p1_elo"] #elo before the match. This is set when match is created, and never changed (unless player elo from a match before it changes)
        p2_elo = match["p2_elo"]

        elo_change = calc_elo_change(p1_elo, p2_elo, new_result)

        DB.update_player(player_id=match["player1"], elo=p1_elo + elo_change[0])
        DB.update_player(player_id=match["player2"], elo=p2_elo + elo_change[1])

        return {"old elo":[p1_elo,p2_elo], "change":elo_change}

    #set the new outcome based on player declare or staff declare
    old_outcome = match["outcome"]
    new_outcome = old_outcome

    if result==results.CANCEL:
        dec_outcome = result
    if match["player1"] == ctx.author.id:
        win_res = results.PLAYER1
        lose_res = results.PLAYER2
        if result == results.WIN:
            dec_outcome = win_res
        elif result == results.LOSE:
            dec_outcome = lose_res
        DB.update_match(match_id=match_id, p1_declared=dec_outcome) #if dec_outcome isn't initialized yet, error in command input
    elif match["player2"] == ctx.author.id:
        win_res = results.PLAYER2
        lose_res = results.PLAYER1
        if result == results.WIN:
            dec_outcome = win_res
        elif result == results.LOSE:
            dec_outcome = lose_res
        DB.update_match(match_id=match_id, p2_declared=dec_outcome)
    else:
        pass #invalid result

    #refresh match and check whether both declares are equal
    match = get_selected_match()
    if match["p1_declared"] == match["p2_declared"]:
        new_outcome = dec_outcome
    response = "Declared: you " + result + " match " + str(match_id)

    if old_outcome != new_outcome:

        if match_id != DB.get_matches(player=player_id).iloc[0,:]["match_id"]:
            await ctx.respond("Changing the result of old matches isn't supported yet")  # for now
            DB.close_connection()
            return

        elo_change = await update_players_elo(old_outcome, new_outcome) #updates everyone's elo accordingly, based on the current selected match
        DB.update_match(match_id, outcome=new_outcome)

        #display results
        p1_info = DB.get_players(user_id=match["player1"]).iloc[0,:]
        p2_info = DB.get_players(user_id=match["player2"]).iloc[0,:]
        p1_current_elo = p1_info["elo"]
        p2_current_elo = p2_info["elo"]
        p1_name = p1_info["username"]
        p2_name = p2_info["username"]
        await ctx.get_channel().send(
            "Match " + str(match_id) + " results: " + str(new_outcome) +
            "\n" + str(p1_name) + ": " + str(round(elo_change["old elo"][0])) + " + " + str(round(elo_change["change"][0])) + " = " + str(round(p1_current_elo)) +\
            "\n" + str(p2_name) + ": " + str(round(elo_change["old elo"][1])) + " + " + str(round(elo_change["change"][1])) + " = " + str(round(p2_current_elo))
        )

    DB.close_connection()
    await ctx.respond(response)


@component.with_slash_command
@tanjun.as_slash_command("queue", "queue status", default_to_ephemeral=False)
async def get_leaderboard(ctx: tanjun.abc.Context) -> None:

    raise NotImplementedError



@component.with_slash_command
@tanjun.as_slash_command("match", "Your latest match's status", default_to_ephemeral=True)
async def get_match(ctx: tanjun.abc.Context) -> None:

    player_id = ctx.author.id

    DB.open_connection()

    match = DB.get_matches(player=player_id, is_full=True).iloc[0,:]

    print("outcome: " + str(match["outcome"]))

    if match["outcome"]==results.PLAYER1:
        winner_id = match["player1"]
        result = DB.get_players(user_id=winner_id).iloc[0,:]["username"]
    elif match["outcome"] == results.PLAYER2:
        winner_id = match["player2"]
        result = DB.get_players(user_id=winner_id).iloc[0,:]["username"]
    elif match["outcome"] == results.CANCEL:
        result = "cancelled"
    else:
        result = "undecided"

    await ctx.respond("Match " + str(match["match_id"]) + " winner: " + result)



@component.with_slash_command
@tanjun.as_slash_command("lb", "leaderboard", default_to_ephemeral=False)
async def get_leaderboard(ctx: tanjun.abc.Context) -> None:

    DB.open_connection()
    players = DB.get_players(top_by_elo=20)

    response = "Leaderboard:\n"
    place = 0
    for player_id in players.index:
        place = place + 1
        player = players.loc[player_id]
        response = response + str(place) + ": " + str(player["username"]) + ": " + str(round(player["elo"])) + "\n"

    await ctx.respond(response, delete_after=200)
    DB.close_connection()


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



@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())