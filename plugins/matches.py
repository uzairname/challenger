import hikari
import tanjun
from utils.ELO import *
from database import Database

component = tanjun.Component(name="matches module")


@component.with_slash_command
@tanjun.with_str_slash_option("result", "result", choices={"win":Declare.WIN, "loss":Declare.LOSS, "draw":Declare.DRAW, "cancel":Declare.CANCEL})
@tanjun.as_slash_command("declare", "declare a match's results", default_to_ephemeral=True, always_defer=True)
@check_errors
@ensure_registered
async def declare_match(ctx: tanjun.abc.SlashContext, result, client=tanjun.injected(type=tanjun.abc.Client)) -> None:

    DB = Database(ctx.guild_id)

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
    is_p1 = match["p1_id"] == ctx.author.id
    DECLARE_TO_RESULT = {
        Declare.WIN: Result.PLAYER_1 if is_p1 else Result.PLAYER_2,
        Declare.LOSS: Result.PLAYER_2 if is_p1 else Result.PLAYER_1,
        Declare.DRAW: Result.DRAW,
        Declare.CANCEL: Result.CANCEL
    }
    new_outcome = DECLARE_TO_RESULT[result]
    if is_p1:
        match["p1_declared"] = new_outcome
    else:
        match["p2_declared"] = new_outcome

    #update the match in the database
    DB.upsert_match(match)

    await ctx.respond("Declared " + str(result) + " for match " + str(match.name))
    #TODO: edit match results message for declares

    #check whether both declares match
    if match["p1_declared"] == match["p2_declared"]:
        return await set_match_outcome(ctx, match.name, new_outcome, client)

@component.with_slash_command
@tanjun.as_slash_command("match-history", "Your latest matches' results", default_to_ephemeral=True, always_defer=True)
@check_errors
@ensure_registered
async def match_history_cmd(ctx: tanjun.abc.Context) -> None:

    DB = Database(ctx.guild_id)

    matches = DB.get_matches(user_id=ctx.author.id, number=5).sort_index(ascending=True) #5 matches per page

    print(matches)

    if matches.empty:
        await ctx.respond("you haven't played any matches")
        return

    embeds = []

    for match_id, match in matches.iterrows():

        p1_name = DB.get_players(user_id=match["p1_id"]).loc[0, "username"]
        p2_name = DB.get_players(user_id=match["p2_id"]).loc[0, "username"]

        p1_prior_elo_message = str(round(match["p1_elo"]))
        if not match["p1_is_ranked"]:
            p1_prior_elo_message += "?"
        p2_prior_elo_message = str(round(match["p2_elo"]))
        if not match["p2_is_ranked"]:
            p2_prior_elo_message += "?"

        if match["outcome"] == Result.PLAYER_1:
            winner_id = match["p1_id"]
            result = str(DB.get_players(user_id=winner_id).iloc[0]["username"]) + " won"
        elif match["outcome"] == Result.PLAYER_2:
            winner_id = match["p1_id"]
            result = str(DB.get_players(user_id=winner_id).iloc[0]["username"]) + " won"
        elif match["outcome"] == Result.CANCEL:
            result = "Cancelled"
        elif match["outcome"] == Result.DRAW:
            result = "Draw"
        else:
            result = "Undecided"

        embed = Custom_Embed(type=Embed_Type.INFO, title="Match " + str(match.name))

        result_declared = "Undecided"
        if match["p1_declared"] == Result.PLAYER_1:
            p1_declared = "Declared win"
        elif match["p1_declared"] == Result.PLAYER_2:
            p1_declared = "Declared loss"
        elif match["p1_declared"] is None:
            p1_declared = "Didn't declare"
        else:
            p1_declared = match["p1_declared"]
        if match["p2_declared"] == Result.PLAYER_2:
            p2_declared = "Declared win"
        elif match["p2_declared"] == Result.PLAYER_1:
            p2_declared = "Declared loss"
        elif match["p2_declared"] is None:
            p2_declared = "Didn't declare"
        else:
            p2_declared = match["p2_declared"]

        embed.add_field(name=result, value="*_ _*")

        embed.add_field(name=str(p1_name), value="Elo: " + p1_prior_elo_message + "\n " + p1_declared, inline=True)
        embed.add_field(name="vs", value="*_ _*", inline=True)
        embed.add_field(name=str(p2_name), value="Elo: " + p2_prior_elo_message + "\n " + p2_declared, inline=True)

        embed.set_footer(text="time: " + str(match["time_started"]))

        embeds.append(embed)

    await ctx.edit_initial_response(embeds=embeds)


@component.with_slash_command
@tanjun.with_str_slash_option("outcome", "set the outcome", choices={"1":Result.PLAYER_1, "2":Result.PLAYER_2, "draw":Result.DRAW, "cancel":Result.CANCEL})
@tanjun.with_str_slash_option("match_number", "Enter the match number")
@tanjun.as_slash_command("setmatch", "set a match's outcome", default_to_ephemeral=False, always_defer=True)
@check_errors
@ensure_staff
@ensure_registered
async def set_match(ctx: tanjun.abc.Context, match_number, outcome, client=tanjun.injected(type=tanjun.abc.Client)):

    DB = Database(ctx.guild_id)

    matches = DB.get_matches(match_id=match_number)
    if matches.empty:
        await ctx.edit_initial_response("No match found")
        return
    match = matches.iloc[0]

    return await set_match_outcome(ctx, match.name, outcome, client, staff_declared=True)


def update_match(matches, match_id, new_outcome=None, updated_players=None):
    updated_players = updated_players or {}

    match = matches.loc[match_id]

    p1_id = match["p1_id"]
    p2_id = match["p2_id"]

    p1_elo = match["p1_elo"]
    p2_elo = match["p2_elo"]

    for i in updated_players:
        if i == p1_id:
            p1_elo = updated_players[i]
            matches.loc[match_id, "p1_elo"] = p1_elo

        if i == p2_id:
            p2_elo = updated_players[i]
            matches.loc[match_id, "p2_elo"] = p2_elo

    outcome = match["outcome"]
    if new_outcome is not None:
        outcome = new_outcome
        matches.loc[match_id, "outcome"] = new_outcome

    #If this match should be affected in any way, calculate the players' new elos. If not, move on to the next match
    if p1_id in updated_players.keys() or p2_id in updated_players.keys() or new_outcome is not None:

        if not matches.loc[match_id, "p1_is_ranked"]: #only determine whether they're ranked if they're not already ranked
            matches.loc[match_id, "p1_is_ranked"] = determine_is_ranked(matches, player_id=p1_id, latest_match_id=match_id)

        if not matches.loc[match_id, "p2_is_ranked"]:
            matches.loc[match_id, "p2_is_ranked"] = determine_is_ranked(matches, player_id=p2_id, latest_match_id=match_id)

        if matches.loc[match_id, "p1_is_ranked"]:
            p1_elo_after = p1_elo + calc_elo_change(p1_elo, p2_elo, outcome)[0]
        else:
            p1_elo_after = p2_elo + calc_prov_elo(p1_elo, p2_elo, outcome)[1]

        if matches.loc[match_id, "p2_is_ranked"]:
            p2_elo_after = p1_elo + calc_elo_change(p2_elo, p1_elo, outcome)[0]
        else:
            p2_elo_after = p2_elo + calc_prov_elo(p2_elo, p1_elo, outcome)[1]

        updated_players[p1_id] = p1_elo_after
        updated_players[p2_id] = p2_elo_after

    # do the same to the next match
    if matches[match_id+1:].empty:
        return matches, updated_players
    else:
        return update_match(matches, match_id + 1, updated_players=updated_players)


def determine_is_ranked(all_matches, player_id, latest_match_id):
    """
        Counts all the matches the player has played in before the current match that weren't cancelled or undecided
        if they have played enough matches, they are ranked
    """

    player_matches = all_matches.loc[np.logical_or(all_matches["p1_id"] == player_id, all_matches["p2_id"] == player_id)]\
    .loc[all_matches.index <= latest_match_id]\
    .loc[np.logical_or(all_matches["outcome"] == Result.PLAYER_1, all_matches["outcome"] == Result.PLAYER_2, all_matches["outcome"] == Result.DRAW)]

    return len(player_matches) >= Config.NUM_UNRANKED_MATCHES


def get_provisional_game_results(all_matches, player_id, latest_match_id): #TODO: support draws

    player_matches = all_matches.loc[np.logical_or(all_matches["p1_id"] == player_id, all_matches["p2_id"] == player_id)]
    player_matches = player_matches.loc[player_matches.index <= latest_match_id]

    results = []

    for match_id, match in player_matches.iterrows():
        if match["outcome"] == Result.CANCEL or match["outcome"] == Result.DRAW or match["outcome"] == Result.UNDECIDED or match["outcome"] is None:
            continue

        if match["p1_id"] == player_id:
            winning_outcome = Result.PLAYER_1
            opponent_elo = match["p2_elo"]
        else:
            winning_outcome = Result.PLAYER_2
            opponent_elo = match["p1_elo"]

        if match["outcome"] == winning_outcome:
            results.append(("win", opponent_elo))
        else:
            results.append(("loss", opponent_elo))

    return results



async def set_match_outcome(ctx:tanjun.abc.Context, match_id, new_outcome, client:tanjun.abc.Client=tanjun.injected(type=tanjun.abc.Client), staff_declared=None):

    DB = Database(ctx.guild_id)
    matches = DB.get_matches()
    match = matches.loc[match_id]

    try:
        p1 = DB.get_players(user_id=match["p1_id"]).iloc[0]
        p2 = DB.get_players(user_id=match["p2_id"]).iloc[0]
    except IndexError:
        return await ctx.respond(embed=Custom_Embed(type=Embed_Type.ERROR, description="One of the players in this match doesn't exist anymore"))

    if match["outcome"] == new_outcome:
        return await ctx.edit_initial_response("Outcome is already " + str(new_outcome))

    if staff_declared:
        matches.loc["staff_declared"] = new_outcome

    matches, updated_players = update_match(matches, match.name, new_outcome)

    DB.upsert_matches(matches)

    print("Updated players: " + str(updated_players))


    #create the announcement message

    # p1_ping = "<@" + str(match["p1_id"]) + ">"
    # p2_ping = "<@" + str(match["p2_id"]) + ">"
    #
    # p1_elo_change = str(round(p1_elo_after - match["p1_elo"], 1))
    # if p1_elo_change[0] != "-":
    #     p1_elo_change = "+" + p1_elo_change
    # p2_elo_change = str(round(p2_elo_after - match["p2_elo"] , 1))
    # if p2_elo_change[0] != "-":
    #     p2_elo_change = "+" + p2_elo_change
    #
    # p1_prior_elo_message = str(round(match["p1_elo"]))
    # if not match["p1_is_ranked"]:
    #     p1_prior_elo_message += "?"
    # p2_prior_elo_message = str(round(match["p2_elo"]))
    # if not match["p2_is_ranked"]:
    #     p2_prior_elo_message += "?"
    #
    # p1_elo_after_message = str(round(p1_elo_after))
    # if not p1_ranked_after:
    #     p1_elo_after_message += "?"
    # p2_elo_after_message = str(round(p2_elo_after))
    # if not p2_ranked_after:
    #     p2_elo_after_message += "?"
    #
    # result_embed = hikari.Embed(title="Match " + str(match.name) + " results: " + str(new_outcome), description="", color=Colors.PRIMARY)
    # result_embed.add_field(name="Player 1", value=p1_ping + ": " + p1_prior_elo_message + " (" + p1_elo_change + ")" + " -> " + p1_elo_after_message, inline=True)
    # result_embed.add_field(name="Player 2", value=p2_ping + ": " + p2_prior_elo_message + " (" + p2_elo_change + ")" + " -> " + p2_elo_after_message, inline=True)
    #
    # if staff_declared:
    #     result_embed.add_field(name="Result overriden by staff", value=f"(Set by {ctx.author.username}#{ctx.author.discriminator})")

    # #send the announcement message
    # config = DB.get_config()
    # channel_id = config["results_channel"]
    #
    # if channel_id is None:
    #     await ctx.get_channel().send("\nNo match announcements channel specified. Announcing here", embed=result_embed)
    #     return
    # await client.rest.create_message(channel_id, embed=result_embed)


@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())