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

def is_registered(ctx: tanjun.abc.Context, DB:Database) -> bool:
    player = DB.get_players(user_id=ctx.author.id)
    if player.empty:
        return False
    return True


async def get_available_queue(ctx:tanjun.abc.Context, DB:Database) -> pd.Series:
    queue = DB.get_queues(ctx.channel_id)
    if queue.empty:
        await ctx.edit_initial_response("This channel doesn't have a lobby")
        return
    return queue.iloc[0]


async def start_new_match(ctx:tanjun.abc.Context, queue, p1_info, p2_info):
    DB = Database(ctx.guild_id)

    p1_ping = "<@" + str(p1_info["user_id"]) + ">"
    p2_ping = "<@" + str(p2_info["user_id"]) + ">"

    new_match = DB.get_new_match()
    new_match[["player_1", "player_2", "p1_elo", "p2_elo", "p1_is_ranked", "p2_is_ranked"]] = [p1_info["user_id"], p2_info["user_id"], p1_info["elo"],
                                                               p2_info["elo"], p1_info["is_ranked"], p2_info["is_ranked"]]


    DB.upsert_match(new_match)
    queue["player"] = None

    await ctx.get_channel().send("Match " + str(new_match["match_id"]) + " started: " + p1_ping + " vs " + p2_ping, user_mentions=True)




async def update_match_outcome(ctx:tanjun.abc.Context, match, new_outcome, staff_declared=False):

    DB = Database(ctx.guild_id)

    p1 = DB.get_players(user_id=match["player_1"]).iloc[0]
    p2 = DB.get_players(user_id=match["player_2"]).iloc[0]

    #make sure this is the most recent match for both players
    p1_latest_match = DB.get_matches(user_id=p1["user_id"]).iloc[0]["match_id"]
    p2_latest_match = DB.get_matches(user_id=p2["user_id"]).iloc[0]["match_id"]

    if p1_latest_match != match["match_id"] or p2_latest_match != match["match_id"]:
        await ctx.edit_initial_response("Unable to change old match results")# Changing the result of an old match has a cascading effect on all the subsequent players those players played against, and the players they played against, and so on... since your elo change depends on your and your opponent's prior elo. If the changed match is very old, the calculation might take a while
        return

    standard_elo_change = calc_elo_change(match["p1_elo"], match["p2_elo"], new_outcome)

    #check whether player's elo is provisional
    p1_ranked_after, p2_ranked_after = False, False
    if match["p1_is_ranked"]:
        p1_elo_after = match["p1_elo"] + standard_elo_change[0]
        p2_ranked_after = True

    else:
        p1_elo_after = match["p1_elo"] + standard_elo_change[0]*3

        p1_matches = DB.get_matches(user_id=match["player_1"], number=NUM_UNRANKED_MATCHES, ascending=True)

        print("p1_matches:", p1_matches)

        if len(p1_matches.index) >= NUM_UNRANKED_MATCHES:
            p1_ranked_after = True

    if match["p2_is_ranked"]:
        p2_elo_after = match["p2_elo"] + standard_elo_change[1]
        p2_ranked_after = True
    else:
        p2_elo_after = match["p2_elo"] + standard_elo_change[1]*3 #temp

        p2_matches = DB.get_matches(user_id=match["player_2"], number=NUM_UNRANKED_MATCHES, ascending=True)

        print("p2_matches", p2_matches)

        if len(p2_matches.index) >= NUM_UNRANKED_MATCHES:
            p2_ranked_after = True



    #after updating all the matches then

    p1["elo"] = p1_elo_after
    p2["elo"] = p2_elo_after

    if p1_ranked_after:
        p1["is_ranked"] = p1_ranked_after

    if p2_ranked_after:
        p2["is_ranked"] = p2_ranked_after


    print("p1 ranked before: ", match["p1_is_ranked"])
    print("p1 ranked after: ", p1["is_ranked"])

    print("p2 ranked before: ", match["p2_is_ranked"])
    print("p2 ranked after: ", p2["is_ranked"])

    DB.upsert_player(p1)
    DB.upsert_player(p2)

    match["outcome"] = new_outcome
    match["staff_declared"] = staff_declared
    DB.upsert_match(match)

    #create the announcement message

    p1_ping = "<@" + str(match["player_1"]) + ">"
    p2_ping = "<@" + str(match["player_2"]) + ">"

    p1_elo_change = str(round(p1_elo_after - match["p1_elo"], 1))
    if p1_elo_change[0] != "-":
        p1_elo_change = "+" + p1_elo_change
    p2_elo_change = str(round(p2_elo_after - match["p2_elo"] , 1))
    if p2_elo_change[0] != "-":
        p2_elo_change = "+" + p2_elo_change

    p1_prior_elo_message = str(round(match["p1_elo"]))
    if not match["p1_is_ranked"]:
        p1_prior_elo_message += "?"
    p2_prior_elo_message = str(round(match["p2_elo"]))
    if not match["p2_is_ranked"]:
        p2_prior_elo_message += "?"

    p1_elo_after_message = str(round(p1_elo_after))
    if not p1_ranked_after:
        p1_elo_after_message += "?"
    p2_elo_after_message = str(round(p2_elo_after))
    if not p2_ranked_after:
        p2_elo_after_message += "?"

    result_embed = hikari.Embed(title="Match " + str(match["match_id"]) + " results: " + str(new_outcome), description="", color=Colors.PRIMARY)
    result_embed.add_field(name="Player 1", value=p1_ping + ": " + p1_prior_elo_message + " -> " + p1_elo_after_message + " (" + p1_elo_change + ")", inline=True)
    result_embed.add_field(name="Player 2", value=p2_ping + ": " + p2_prior_elo_message + " -> " + p2_elo_after_message + " (" + p2_elo_change + ")", inline=True)

    if staff_declared:
        result_embed.add_field(name="Result overriden by staff", value=f"(Set by {ctx.author.username}#{ctx.author.discriminator})")

    #send the announcement message
    config = DB.get_config()
    channel_id = config["results_channel"]

    if channel_id is None:
        await ctx.get_channel().send("\nNo match announcements channel specified. Announcing here", embed=result_embed)
        return

    await bot.rest.create_message(channel_id, embed=result_embed)




#join the queue
@component.with_slash_command
@tanjun.as_slash_command("join", "join the queue", default_to_ephemeral=True)
async def join_q(ctx: tanjun.abc.Context) -> None:

    await ctx.respond("please wait")

    DB = Database(ctx.guild_id)

    #Ensure the current channel has a queue associated with it
    queue = await get_available_queue(ctx, DB)
    if queue is None:
        return

    if not is_registered(ctx, DB):
        await ctx.respond(f"Hi {ctx.author.mention}! Please register with /register to play", user_mentions=True)
        return


    #Ensure player has at least 1 role required by the queue
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
            if match["player_1"] == player_id and match["p1_declared"] is None or match["player_2"] == player_id and match["p2_declared"] is None:
                await ctx.edit_initial_response("You need to /declare the results for match " + str(match["match_id"]))
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
@tanjun.as_slash_command("leave", "leave the queue", default_to_ephemeral=True)
async def leave_q(ctx: tanjun.abc.Context) -> None:

    await ctx.respond("please wait")

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

    await ctx.respond("please wait")

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

    response = "Declared " + str(result) + " for match " + str(match["match_id"])

    #refresh match and check whether both declares are equal

    if match["p1_declared"] == match["p2_declared"]:
        new_outcome = declared_result

        if match["outcome"] != new_outcome:
            await update_match_outcome(ctx, match, new_outcome)
        else:
            response += "\nOutcome is already " + str(new_outcome)

    await ctx.edit_initial_response(response)

    DB.upsert_match(match)



def get_first_match_results(ctx:tanjun.abc.Context, DB, num_matches, player_id):

    matches = DB.get_matches(user_id=player_id, limit=num_matches)
    if matches.empty:
        return matches
    matches = matches.sort_values(by="match_id", ascending=True)
    return matches.iloc[:num_matches]





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

    await ctx.respond("please wait")

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
@tanjun.with_str_slash_option("outcome", "set the outcome", choices={"1":results.PLAYER_1, "2":results.PLAYER_2, "draw":results.DRAW, "cancel":results.CANCEL})
@tanjun.with_str_slash_option("match_number", "Enter the match number")
@tanjun.as_slash_command("set", "set a match's outcome", default_to_ephemeral=False)
async def force_match(ctx: tanjun.abc.Context, match_number, outcome):

    await ctx.respond("please wait")

    DB = Database(ctx.guild_id)

    if not await is_staff(ctx, DB):
        await ctx.edit_initial_response("Missing permissions")
        return

    player_info = await ensure_registered(ctx, DB)
    if player_info is None:
        return



    matches = DB.get_matches(match_id=match_number)
    if matches.empty:
        await ctx.edit_initial_response("No match found")
        return
    match = matches.iloc[0]

    if match["outcome"] != outcome:
        await update_match_outcome(ctx, match, outcome, True)
        await ctx.edit_initial_response("Match " + str(match["match_id"]) + " updated")
    else:
        await ctx.edit_initial_response("Outcome is already " + str(outcome))






@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())