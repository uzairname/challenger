import logging

from plugins.utils import *
from __main__ import DB




component = tanjun.Component(name="queue module")

#join the queue (if new, register)
@component.with_slash_command
@tanjun.as_slash_command("join", "join the queue", default_to_ephemeral=True)
async def join_q(ctx: tanjun.abc.Context) -> None:

    DB.open_connection()

    #check if player is registered
    player_id = ctx.author.id
    player_info = DB.get_players(user_id=player_id)
    if player_info.empty:
        await ctx.respond(f"hello {ctx.author.mention}. Please register with /register to play")
        DB.close_connection()
        return

    match = DB.get_matches().iloc[0,:]

    #assuming latest match shoud never have 2 ppl, this should never happen
    if match["player1"] and match["player2"]:
        await ctx.get_channel().send("Match was full, creating new match")
        DB.create_match()
        match = DB.get_matches().iloc[0, :]

    #check whether player is in the latest match
    if match["player1"] == player_id or match["player2"] == player_id:
        await ctx.respond(f"{ctx.author.mention} you're already in the queue")
        DB.close_connection()
        return

    logging.info("Adding player to match")
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
@tanjun.with_str_slash_option("result", "result", choices={"won":results.WIN, "lost":results.LOSE, "cancel":results.CANCEL, "player 1":results.PLAYER1, "player 2":results.PLAYER2})
@tanjun.as_slash_command("declare", "declare a match's results", default_to_ephemeral=True)
async def declare_match(ctx: tanjun.abc.SlashContext, result, match_number) -> None:

    DB.open_connection()
    player_id = ctx.author.id
    player_info = DB.get_players(user_id=player_id)

    print("player info:\n" + str(player_info))
    print("\n" + str(player_info["role"]))

    isStaff = False

    print("staff : " + str(isStaff))

    try:
        def get_selected_match():
            if isStaff:
                return DB.get_matches(match_id=match_number).iloc[0,:] #don't filter by player if staff
            elif match_number == "latest": #they didn't specify a match number
                return DB.get_matches(player=player_id).iloc[0,:]
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

    #check if match is full
    if match["player1"] is None or match["player2"] is None:
        await ctx.respond("Your match hasn't started")
        DB.close_connection()
        return

    async def update_players_elo(old_result, new_result):

        p1_elo = match["p1_elo"] #elo before the match. This is set when match is created, and never changed (unless player elo from a match before it changes)
        p2_elo = match["p2_elo"]

        elo_change = calc_elo_change(p1_elo, p2_elo, new_result)

        DB.update_player(player_id=match["player1"], elo=p1_elo + elo_change[0])
        DB.update_player(player_id=match["player2"], elo=p2_elo + elo_change[1])

        return {"old elo":[p1_elo,p2_elo], "change":elo_change}

    #set the new outcome based on player declare or staff declare
    old_outcome = match["outcome"]
    new_outcome = old_outcome
    dec_outcome = result if isStaff else None

    if result==results.CANCEL:
        dec_outcome = result
    if match["player1"] == ctx.author.id:
        win_res = results.PLAYER1
        lose_res = results.PLAYER2
        if result == results.WIN:
            dec_outcome=win_res
        elif result == results.LOSE:
            dec_outcome=lose_res
        DB.update_match(match_id=match_id, p1_declared=dec_outcome)
    elif match["player2"] == ctx.author.id:
        win_res = results.PLAYER2
        lose_res = results.PLAYER1
        if result == results.WIN:
            dec_outcome=win_res
        elif result == results.LOSE:
            dec_outcome=lose_res
        DB.update_match(match_id=match_id, p2_declared=dec_outcome)

    if isStaff:
        new_outcome = dec_outcome
        response = "Declared by staff: " + str(new_outcome)
    else: #check whether both declares are equal
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
        p1_current = DB.get_players(user_id=match["player1"]).iloc[0,:]["elo"]
        p2_current = DB.get_players(user_id=match["player2"]).iloc[0,:]["elo"]
        await ctx.get_channel().send(
            "Match " + str(match_id) + " results: " + str(new_outcome) +
            "\n Player 1: " + str(elo_change["old elo"][0]) + " + " + str(elo_change["change"][0]) + " = " + str(p1_current) +\
            "\n Player 2: " + str(elo_change["old elo"][1]) + " + " + str(elo_change["change"][1]) + " = " + str(p2_current)
        )

    DB.close_connection()
    await ctx.respond(response)




@component.with_slash_command
@tanjun.as_slash_command("match", "Your latest match's status", default_to_ephemeral=True)
async def get_match(ctx: tanjun.abc.Context) -> None:

    player_id = ctx.author.id

    DB.open_connection()

    match = DB.get_matches(player=player_id).iloc[0,:]

    print("outcome: " + str(match["outcome"]))

    result = "undecided"
    if match["outcome"]==results.PLAYER1:
        winner_id = match["player1"]
        result = DB.get_players(user_id=winner_id).iloc[0,:]["username"]
    elif match["outcome"] == results.PLAYER2:
        winner_id = match["player2"]
        result = DB.get_players(user_id=winner_id).iloc[0,:]["username"]
    elif match["outcome"] == results.CANCEL:
        result = "cancelled"

    await ctx.respond("Winner: " + result)




@component.with_slash_command
@tanjun.as_slash_command("lb", "leaderboard", default_to_ephemeral=False)
async def get_match(ctx: tanjun.abc.Context) -> None:

    DB.open_connection()
    players = DB.get_players(top_by_elo=20)

    response = ""
    for player_id in players.index:
        player = players.loc[player_id]
        response = response + str(player["username"]) + ": " + str(player["elo"]) + "\n"

    await ctx.respond(response)
    DB.close_connection()



@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())