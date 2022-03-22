import logging

import tanjun
import functools
from plugins.utils import *
from database import Database
from __main__ import bot


component = tanjun.Component(name="queue module")


async def ensure_registered(ctx: tanjun.abc.Context, DB:Database) -> pd.Series:
    player = DB.get_players(user_id=ctx.author.id)
    if player.empty:
        await ctx.respond(f"hello {ctx.author.mention}. Please register with /register to play", user_mentions=True)
        return
    return player.iloc[0]


async def get_available_queue(ctx:tanjun.abc.Context, DB:Database) -> pd.Series:
    queue = DB.get_queues(ctx.channel_id)
    if queue.empty:
        await ctx.respond("This channel doesn't have a lobby")
        return
    return queue.iloc[0]


#join the queue
@component.with_slash_command
@tanjun.as_slash_command("join", "join the queue", default_to_ephemeral=True)
async def join_q(ctx: tanjun.abc.Context) -> None:

    DB = Database(ctx.guild_id)

    #Ensure the current channel has a queue associated with it
    queue = await get_available_queue(ctx, DB)
    if queue.empty:
        print("queue didn't exist")
        return

    player_info = await ensure_registered(ctx, DB)
    if player_info is None:
        return

    #Ensure player has at least 1 role required by the queue
    is_allowed = False
    print(ctx.member.role_ids)
    for role in queue["roles"]:
        print(str(role) + ", ")
        if role in ctx.member.role_ids:
            is_allowed = True
    if not is_allowed:
        await ctx.respond("You're not allowed to join this lobby")
        return


    config_settings = DB.get_config()
    rbe = config_settings["roles_by_elo"]
    for index, row in rbe.iterrows():
        print("role: " + str(index) + "\n with range:" + str(row["min"]) + " to " + str(row["max"]))


    player_id=ctx.author.id

    #Ensure player isn't already in queue
    if queue["player"] == player_id:
        await ctx.respond(f"{ctx.author.mention} you're already in the queue")
        return

    #add player to queue
    print(str(queue["player"]) + " is " + str(bool(queue["player"])) + str(type(queue["player"])))
    if not queue["player"]:
        queue["player"] = player_id
        await ctx.edit_initial_response(f"{ctx.author.mention} you have silently joined the queue")
        await ctx.get_channel().send("A player has joined the lobby **" + str(queue["lobby_name"]) + "**")
    else:
        await ctx.edit_initial_response(f"{ctx.author.mention} Queue is full. Creating match")
        p1_info = DB.get_players(user_id=queue['player']).iloc[0]
        p2_info = DB.get_players(user_id=player_id).iloc[0]

        print("player1: " + str(p1_info))
        print("player2: " + str(p2_info))

        p1_ping = "<@" + str(p1_info["user_id"]) + ">"
        p2_ping = "<@" + str(p2_info["user_id"]) + ">"

        new_match = DB.get_new_match()
        new_match[["player_1", "player_2", "p1_elo", "p2_elo"]] = [p1_info["user_id"], p2_info["user_id"], p1_info["elo"],p2_info["elo"]]
        print(new_match)
        # DB.add_new_match(player_1=p1_info["user_id"],
        #                  player_2=p2_info["user_id"],
        #                  p1_elo=p1_info["elo"],
        #                  p2_elo=p2_info["elo"])
        DB.upsert_match(new_match)

        queue["player"] = None

        await ctx.get_channel().send("New match started: " + p1_ping + " vs " + p2_ping, user_mentions=True)

    DB.upsert_queue(queue)


#leave queue
@component.with_slash_command
@tanjun.as_slash_command("leave", "leave the queue", default_to_ephemeral=True)
async def leave_q(ctx: tanjun.abc.Context) -> None:

    DB = Database(ctx.guild_id)

    queue = await get_available_queue(ctx, DB)
    if queue is None:
        return

    player_info = await ensure_registered(ctx, DB)
    if player_info is None:
        return

    player_id = ctx.author.id

    response = "Left the queue"
    if queue["player"] == player_id:
        queue["player"] = None
        await ctx.get_channel().send("A player has left the queue")
    else:
        response = "You're not in the queue"

    DB.upsert_queue(queue)
    await ctx.edit_initial_response(response)


class declares:
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
@component.with_slash_command
@tanjun.with_str_slash_option("result", "result", choices={"win":declares.WIN, "loss":declares.LOSS, "draw":declares.DRAW})
@tanjun.as_slash_command("declare", "declare a match's results", default_to_ephemeral=True)
async def declare_match(ctx: tanjun.abc.SlashContext, result) -> None:

    DB = Database(ctx.guild_id)

    player_info = await ensure_registered(ctx, DB)
    if player_info is None:
        return

    match = DB.get_matches(user_id=ctx.author.id)
    if match.empty:
        await ctx.edit_initial_response("You haven't played a match")
        return
    match = match.iloc[0]
        #note: changing the result of an old match has a cascading effect on all the subsequent players those players played against, and the players they played against, and so on... since your elo change depends on your and your opponent's prior elo. If the changed match is very old, the calculation might take a while

        # elo before the match. This is set when match is created, and never changed (unless player elo from a match before it changes)

    #set the new outcome based on player declare or staff declare

    print("match: " + str(match))
    print("outtome: " + str(match["outcome"]))
    old_outcome = match["outcome"]
    new_outcome = old_outcome

    #set the player's declared result in the match
    is_p1 = match["player_1"] == ctx.author.id
    DECLARE_TO_RESULT = {
        declares.WIN: results.PLAYER1 if is_p1 else results.PLAYER2,
        declares.LOSS: results.PLAYER2 if is_p1 else results.PLAYER1,
        declares.DRAW: results.DRAW
    }
    declared_result = DECLARE_TO_RESULT[result]
    if is_p1:
        match["p1_declared"] = declared_result
    else:
        match["p2_declared"] = declared_result

    response = "Declared " + str(result)

    #refresh match and check whether both declares are equal

    if match["outcome"] == declared_result:
        print("outcome: " + str(match["outcome"]))
        response = "Outcome is already " + str(declared_result)

    if match["p1_declared"] == match["p2_declared"]:
        new_outcome = declared_result

    if old_outcome != new_outcome:
        p1 = DB.get_players(user_id=match["player_1"]).iloc[0]
        p2 = DB.get_players(user_id=match["player_2"]).iloc[0]

        elo_change = calc_elo_change(match["p1_elo"], match["p2_elo"], new_outcome)

        p1["elo"] = match["p1_elo"] + elo_change[0]
        p2["elo"] = match["p2_elo"] + elo_change[1]

        DB.upsert_player(p1)
        DB.upsert_player(p2)

        match["outcome"] = new_outcome
        await announce_outcome(ctx, match, p1, p2, new_outcome, elo_change)

    await ctx.respond(response)

    print(str(match["match_id"]) + "\ntype:\n" +str(type(match["match_id"])))
    DB.upsert_match(match)


async def announce_outcome(ctx:tanjun.abc.Context, match, p1, p2, outcome, elo_change):

    DB = Database(ctx.guild_id)

    config = DB.get_config()

    channel_id = config["results_channel"]

    announcement = "Match " + str(match["match_id"]) + " results: " + str(outcome) + \
        "\n" + str(p1["username"]) + ": " + str(round(match["p1_elo"])) + " + " + str(
            round(elo_change[0], 1)) + " = " + str(round(p1["elo"])) + \
        "\n" + str(p2["username"]) + ": " + str(round(match["p2_elo"])) + " + " + str(
            round(elo_change[1], 1)) + " = " + str(round(p2["elo"]))


    if channel_id is None:
        await ctx.get_channel().send(announcement + "\nNo match announcements channel specified")
        return

    await bot.rest.create_message(channel_id, announcement)




@component.with_slash_command
@tanjun.as_slash_command("queue", "queue status", default_to_ephemeral=False)
async def get_leaderboard(ctx: tanjun.abc.Context) -> None:

    DB = Database(ctx.guild_id)

    queue = await get_available_queue(ctx, DB)
    if queue is None:
        return

    if queue["player"]:
        await ctx.edit_initial_response("1 player in queue")
    else:
        await ctx.edit_initial_response("queue is empty")



@component.with_slash_command
@tanjun.as_slash_command("match", "Your latest match's status", default_to_ephemeral=True)
async def get_match(ctx: tanjun.abc.Context) -> None:

    DB = Database(ctx.guild_id)

    player_info = await ensure_registered(ctx, DB)
    if player_info is None:
        return

    matches = DB.get_matches(user_id=ctx.author.id)
    if matches.empty:
        await ctx.respond("you haven't played any matches")
        return
    match = matches.iloc[0]

    if match["outcome"]==results.PLAYER1:
        winner_id = match["player_1"]
        result = DB.get_players(user_id=winner_id).iloc[0]["username"]
    elif match["outcome"] == results.PLAYER2:
        winner_id = match["player_2"]
        result = DB.get_players(user_id=winner_id).iloc[0]["username"]
    elif match["outcome"] == results.CANCEL:
        result = "cancelled"
    elif match["outcome"] == results.DRAW:
        result = "draw"
    else:
        result = "undecided"

    await ctx.respond("Match " + str(match["match_id"]) + " outcome: " + str(result))



@component.with_slash_command
@tanjun.as_slash_command("lb", "leaderboard", default_to_ephemeral=False)
async def get_leaderboard(ctx: tanjun.abc.Context) -> None:

    DB = Database(ctx.guild_id)

    players = DB.get_players(top_by_elo=[0,20])

    response = "Leaderboard:```\n"
    place = 0

    for index, player, in players.iterrows():
        place = place + 1
        response = response + str(place) + ":\t" + str(round(player["elo"])) + "\t" + str(player["username"]) + "\n"
    response = response + "```"

    await ctx.respond(response)


@component.with_slash_command
@tanjun.as_slash_command("set", "set a match's outcome", default_to_ephemeral=False)
def force_match(ctx: tanjun.abc.Context):
    pass




@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())