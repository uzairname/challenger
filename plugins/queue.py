import logging

from plugins.utils import *
from __main__ import DB


component = tanjun.Component(name="queue module")

def ensure_registered(cmd_func):
    @functools.wraps(cmd_func)
    async def wrapper_ensure_registered(ctx, *args, **kwargs):
        DB.open_connection(guild_id=ctx.guild_id)
        player_info = DB.get_players(user_id=ctx.author.id)
        if player_info.empty:
            await ctx.respond(f"hello {ctx.author.mention}. Please register with /register to play", user_mentions=True)
            DB.close_connection()
            return
        return await cmd_func(ctx, *args, **kwargs)
    return wrapper_ensure_registered

#join the queue
@component.with_slash_command
@tanjun.as_slash_command("join", "join the queue", default_to_ephemeral=True)
@ensure_registered
async def join_q(ctx: tanjun.abc.Context) -> None:

    player_id=ctx.author.id

    #Ensure the current channel has a queue associated with it
    all_queues = DB.get_queues()
    queue = None
    for id in all_queues["queue_id"]:
        if ctx.channel_id in all_queues.loc[id, "channels"]:
            queue = all_queues.loc[id,:]
            break
    if queue is None:
        await ctx.respond("This channel doesn't have a lobby")
        DB.close_connection()
        return

    #Ensure player isn't already in queue
    if queue["player1"] == player_id or queue["player2"] == player_id:
        await ctx.respond(f"{ctx.author.mention} you're already in the queue")
        DB.close_connection()
        return


    #add player to queue
    if not queue["player1"]:
        DB.update_queue(queue_id=queue["queue_id"], player1=player_id)
    elif not queue["player2"]:
        DB.update_queue(queue_id=queue["queue_id"], player2=player_id)
    else:
        await ctx.respond("Queue is full")
        DB.close_connection()#idk
        return
    response = f"{ctx.author.mention} you have silently joined the queue"


    #If queue is full, announce the match
    queue = DB.get_queues().loc[queue["queue_id"],:] #refresh the variable

    if queue["player1"] and queue["player2"]:

        player1_ping = "<@" + str(queue["player1"]) + ">"
        player2_ping = "<@" + str(queue["player2"]) + ">"

        DB.create_match()
        DB.update_match(match_id=DB.get_recent_matches().iloc[0,:]["match_id"],
                        player1=queue['player1'],
                        player2=queue['player2'],
                        p1_elo=DB.get_players(user_id=queue['player1']).iloc[0,:]["elo"],
                        p2_elo=DB.get_players(user_id=queue['player2']).iloc[0,:]["elo"])

        DB.update_queue(queue_id=queue["queue_id"], player1=None, player2=None)

        await ctx.get_channel().send("New match started: " + player1_ping + " vs " + player2_ping, user_mentions=True)
    else:
        await ctx.get_channel().send("A player has joined the queue")

    DB.close_connection()

    await ctx.respond(response)


#leave queue
@component.with_slash_command
@tanjun.as_slash_command("leave", "leave the queue", default_to_ephemeral=True)
@ensure_registered
async def leave_q(ctx: tanjun.abc.Context) -> None:

    player_id = ctx.author.id


    #Ensure the current channel has a queue associated with it
    all_queues = DB.get_queues()
    queue = None
    for id in all_queues["queue_id"]:
        if ctx.channel_id in all_queues.loc[id, "channels"]:
            queue = all_queues.loc[id,:]
            break
    if queue is None:
        await ctx.respond("This channel doesn't have a lobby")
        DB.close_connection()
        return


    response = "Left the queue"

    if queue["player1"] == player_id:
        DB.update_queue(queue["queue_id"], player1 = None)
        await ctx.get_channel().send("A player has left the queue")
    elif queue["player2"] == player_id:  #Assuming player1 can't leave the match after player2 joins, this should never happen
        DB.update_match(queue["match_id"], player2 = None)
        await ctx.get_channel().send("Player 2 left the queue??")
    else:
        response = f"You're not in the queue"
        await ctx.respond(response)

    DB.close_connection()
    await ctx.respond(response)


class declares:
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
@component.with_slash_command
@tanjun.with_str_slash_option("result", "result", choices={"win":declares.WIN, "loss":declares.LOSS, "draw":declares.DRAW})
@tanjun.as_slash_command("declare", "declare a match's results", default_to_ephemeral=True)
@ensure_registered
async def declare_match(ctx: tanjun.abc.SlashContext, result) -> None:

    DB.open_connection(ctx.guild_id)
    player_id = ctx.author.id
    player_info = DB.get_players(user_id=player_id)

    try:
        match = DB.get_recent_matches(player=player_id).iloc[0,:] #the current match
    except:
        await ctx.respond("No match found")
        DB.close_connection()
        return
    match_id = match["match_id"]
    #check if match is full, won't be needed

    async def update_players_elo(new_result):
        #note: changing the result of an old match has a cascading effect on all the subsequent players those players played against, and the players they played against, and so on... since your elo change depends on your and your opponent's prior elo. If the changed match is very old, the recursive algorithm might take a while

        p1_elo = match["p1_elo"]
        p2_elo = match["p2_elo"] #elo before the match. This is set when match is created, and never changed (unless player elo from a match before it changes)

        elo_change = calc_elo_change(p1_elo, p2_elo, new_result)

        DB.update_player(player_id=match["player1"], elo=p1_elo + elo_change[0])
        DB.update_player(player_id=match["player2"], elo=p2_elo + elo_change[1])

        return {"old elo":[p1_elo,p2_elo], "change":elo_change}

    #set the new outcome based on player declare or staff declare
    old_outcome = match["outcome"]
    new_outcome = old_outcome

    #set the player's declared result in the match
    is_p1 = match["player1"] == ctx.author.id
    get_declared_result = {
        declares.WIN: results.PLAYER1 if is_p1 else results.PLAYER2,
        declares.LOSS: results.PLAYER2 if is_p1 else results.PLAYER1,
        declares.DRAW: results.DRAW
    }
    declared_result = get_declared_result[result]
    if is_p1:
        DB.update_match(match_id=match_id, p1_declared=declared_result)
    else:
        DB.update_match(match_id=match_id, p2_declared=declared_result)

    response = "Declared " + result

    #refresh match and check whether both declares are equal
    match = DB.get_recent_matches(player_id).iloc[0,:]

    if match["outcome"] == declared_result:
        response = "Outcom is already " + str(declared_result)

    if match["p1_declared"] == match["p2_declared"]:
        new_outcome = declared_result

    if old_outcome != new_outcome:
        elo_change = await update_players_elo(new_outcome) #updates everyone's elo accordingly, based on the current selected match
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
    DB.open_connection(ctx.guild_id)

    #get queue for this channel
    all_queues = DB.get_queues()
    queue = None
    for id in all_queues["queue_id"]:
        if ctx.channel_id in all_queues.loc[id, "channels"]:
            queue = all_queues.loc[id,:]
            break
    if queue is None:
        await ctx.respond("This channel doesn't have a lobby")
        DB.close_connection()
        return


    num = 0
    for p in [queue["player1"], queue["player2"]]:
        if p:
            num = num + 1

    response = "Players in queue: " + str(num)

    await ctx.respond(response, delete_after=200)
    DB.close_connection()



@component.with_slash_command
@tanjun.as_slash_command("match", "Your latest match's status", default_to_ephemeral=True)
@ensure_registered
async def get_match(ctx: tanjun.abc.Context) -> None:

    player_id = ctx.author.id

    match = DB.get_recent_matches(player=player_id).iloc[0, :]

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

    DB.open_connection(ctx.guild_id)
    players = DB.get_players(top_by_elo=20)

    response = "Leaderboard:```\n"
    place = 0
    print(players)
    players.sort_values("elo", ascending=False)
    for index, player, in players.iterrows():
        place = place + 1
        response = response + str(place) + ":\t" + str(round(player["elo"])) + "\t" + str(player["username"]) + "\n"
    response = response + "```"
    await ctx.respond(response, delete_after=200)
    DB.close_connection()



@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())