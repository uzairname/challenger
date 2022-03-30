import hikari
from utils.utils import *
from utils.ELO import *
from database import Database
from __main__ import bot


component = tanjun.Component(name="queue module")


async def ensure_registered(ctx: tanjun.abc.Context, DB:Database) -> pd.Series:
    player = DB.get_players(user_id=ctx.author.id)
    if player.empty:
        await ctx.edit_initial_response(f"hello {ctx.author.mention}. Please register with /register to play", user_mentions=True)
        return
    return player.iloc[0]


async def get_available_queue(ctx:tanjun.abc.Context, DB:Database) -> pd.Series:
    queue = DB.get_queues(ctx.channel_id)
    if queue.empty:
        await ctx.edit_initial_response("This channel doesn't have a lobby")
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
    print("q: " + str(queue))
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
            if match["player_1"] == player_id and match["p1_declared"] is None or match["player_2"] == player_id and match["p2_declared"] is None:
                await ctx.edit_initial_response("You need to /declare the results for match " + str(match["match_id"]))
                return

    #add player to queue
    if not queue["player"]:
        queue["player"] = player_id
        await ctx.edit_initial_response(f"You silently joined the queue")
        await ctx.get_channel().send("A player has joined the queue for **" + str(queue["lobby_name"]) + "**")
        DB.upsert_queue(queue)
    else:
        print("█queue: " + str(queue))
        await ctx.edit_initial_response("Queue is full. Creating match")
        queue["player"] = None
        DB.upsert_queue(queue)
        p1_info = DB.get_players(user_id=queue['player']).iloc[0]
        p2_info = DB.get_players(user_id=player_id).iloc[0]
        await start_new_match(ctx, queue, p1_info, p2_info)




async def start_new_match(ctx:tanjun.abc.Context, queue, p1_info, p2_info):
    DB = Database(ctx.guild_id)

    p1_ping = "<@" + str(p1_info["user_id"]) + ">"
    p2_ping = "<@" + str(p2_info["user_id"]) + ">"

    new_match = DB.get_new_match()
    new_match[["player_1", "player_2", "p1_elo", "p2_elo"]] = [p1_info["user_id"], p2_info["user_id"], p1_info["elo"],
                                                               p2_info["elo"]]
    DB.upsert_match(new_match)
    queue["player"] = None

    await ctx.get_channel().send("Match " + str(new_match["match_id"]) + " started: " + p1_ping + " vs " + p2_ping, user_mentions=True)


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


@component.with_slash_command
@tanjun.with_str_slash_option("result", "result", choices={"win":declares.WIN, "loss":declares.LOSS, "draw":declares.DRAW, "cancel":declares.CANCEL})
@tanjun.as_slash_command("declare", "declare a match's results", default_to_ephemeral=True)
async def declare_match(ctx: tanjun.abc.SlashContext, result) -> None:

    DB = Database(ctx.guild_id)

    player_info = await ensure_registered(ctx, DB)
    if player_info is None:
        return

    matches = DB.get_matches(user_id=ctx.author.id)
    if matches.empty:
        await ctx.edit_initial_response("You haven't played a match")
        return
    match = matches.iloc[0]

    #check if result was declared by staf
    if match["staff_declared"]:
        await ctx.edit_initial_response("Staff already finalized this match's result")
        return

    old_outcome = match["outcome"]
    new_outcome = old_outcome

    print()
    #set the player's declared result in the match
    is_p1 = match["player_1"] == ctx.author.id
    DECLARE_TO_RESULT = {
        declares.WIN: results.PLAYER_1 if is_p1 else results.PLAYER_2,
        declares.LOSS: results.PLAYER_2 if is_p1 else results.PLAYER_1,
        declares.DRAW: results.DRAW,
        declares.CANCEL: results.CANCEL
    }
    declared_result = DECLARE_TO_RESULT[result]
    if is_p1:
        match["p1_declared"] = declared_result
    else:
        match["p2_declared"] = declared_result

    response = "Declared " + str(result)

    #refresh match and check whether both declares are equal

    if match["p1_declared"] == match["p2_declared"]:
        new_outcome = declared_result

    if old_outcome != new_outcome:
        await update_match_outcome(ctx, match, new_outcome)

    await ctx.respond(response)

    DB.upsert_match(match)


async def update_match_outcome(ctx:tanjun.abc.Context, match, new_outcome, staff_declared=False):

    if match["outcome"] == new_outcome:
        await ctx.edit_initial_response("outcome is already " + str(new_outcome))
        return

    elo_change = calc_elo_change(match["p1_elo"], match["p2_elo"], new_outcome)

    DB = Database(ctx.guild_id)

    p1 = DB.get_players(user_id=match["player_1"]).iloc[0]
    p2 = DB.get_players(user_id=match["player_2"]).iloc[0]

    #check if their current elo matches their elo after the match
    old_elo_change = calc_elo_change(match["p1_elo"], match["p2_elo"], match["outcome"])
    p1_elo_after = match["p1_elo"] + old_elo_change[0]
    p2_elo_after = match["p2_elo"] + old_elo_change[1]
    print(old_elo_change, match["p1_elo"], match["p2_elo"], p1_elo_after, p2_elo_after)
    if abs(p1_elo_after - p1["elo"]) > 0.000000001 or abs(p2_elo_after - p2["elo"]) > 0.000000001:
        await ctx.edit_initial_response("Unable to change old match's results.") # Changing the result of an old match has a cascading effect on all the subsequent players those players played against, and the players they played against, and so on... since your elo change depends on your and your opponent's prior elo. If the changed match is very old, the calculation might take a while
        return

    match["outcome"] = new_outcome
    match["staff_declared"] = staff_declared
    DB.upsert_match(match)

    p1["elo"] = match["p1_elo"] + elo_change[0]
    p2["elo"] = match["p2_elo"] + elo_change[1]
    DB.upsert_player(p1)
    DB.upsert_player(p2)

    announcement = "Match " + str(match["match_id"]) + " results: " + str(new_outcome) + \
        "\n" + str(p1["username"]) + ": " + str(round(match["p1_elo"])) + " + " + str(
            round(elo_change[0], 1)) + " = " + str(round(p1["elo"])) + \
        "\n" + str(p2["username"]) + ": " + str(round(match["p2_elo"])) + " + " + str(
            round(elo_change[1], 1)) + " = " + str(round(p2["elo"]))

    if staff_declared:
        announcement += f"\n\n(Results set by {ctx.author.username}#{ctx.author.discriminator})"

    config = DB.get_config()
    channel_id = config["results_channel"]

    if channel_id is None:
        await ctx.get_channel().send(announcement + "\nNo match announcements channel specified. Announcing here")
        return

    await bot.rest.create_message(channel_id, announcement)




@component.with_slash_command
@tanjun.as_slash_command("queue", "queue status", default_to_ephemeral=False)
async def queue_status(ctx: tanjun.abc.Context) -> None:

    await ctx.edit_initial_response("...")

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

    if match["outcome"]==results.PLAYER_1:
        winner_id = match["player_1"]
        result = DB.get_players(user_id=winner_id).iloc[0]["username"]
    elif match["outcome"] == results.PLAYER_2:
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
    if players.empty:
        await ctx.respond("No players registered")
        return

    ranked_players = players.loc[pd.notnull(players["elo"])]
    print(ranked_players)
    provisional_players = players.loc[pd.isnull(players["elo"])]

    max_len = 25
    ranked_list = "```"
    place = 0
    for index, player, in ranked_players.iterrows():
        place += 1
        tag = str(player["tag"])[:max_len]
        ranked_list += str(place) + "." + " "*(5-len(str(place))) + tag + ": "  + " "*(max_len-len(tag))  + str(round(player["elo"])) + "\n"

    ranked_list += "```"

    unranked_list = "```"
    provisional_players.sort_values(by="provisional_elo", ascending=True, inplace=True)
    place = 0
    for index, player in provisional_players.iterrows():
        tag = str(player["tag"])[:max_len]
        unranked_list += str(place) + "." + " "*(5-len(str(place))) + tag + ": "  + " "*(max_len-len(tag))  + str(round(player["provisional_elo"])) + "?\n"

    unranked_list += "```"

    ranked_embed = hikari.Embed(title="Leaderboard", description="Page 1: Top 20", color=PELA_CYAN)
    ranked_embed.add_field(name="Rank       Username                                                  Score", value=ranked_list, inline=False)

    unranked_embed = hikari.Embed(title="Unranked", description="Page 1: Top 20", color=PELA_CYAN)
    unranked_embed.add_field(name="Rank       Username                                                  Score", value=unranked_list, inline=False)

    await ctx.respond(embeds=[ranked_embed, unranked_embed])


@component.with_slash_command
@tanjun.with_str_slash_option("outcome", "set the outcome", choices={"1":results.PLAYER_1, "2":results.PLAYER_2, "draw":results.DRAW, "cancel":results.CANCEL})
@tanjun.with_str_slash_option("match_number", "Enter the match number")
@tanjun.as_slash_command("set", "set a match's outcome", default_to_ephemeral=False)
async def force_match(ctx: tanjun.abc.Context, match_number, outcome):

    await ctx.respond("...")

    DB = Database(ctx.guild_id)

    player_info = await ensure_registered(ctx, DB)
    if player_info is None:
        return

    if player_info["staff"] != status.STAFF:
        await ctx.edit_initial_response("Missing permissions")
        return

    matches = DB.get_matches(match_id=match_number)
    if matches.empty:
        await ctx.edit_initial_response("No match found")
        return
    match = matches.iloc[0]
    await update_match_outcome(ctx, match, outcome, True)





@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())