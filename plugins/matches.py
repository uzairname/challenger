import hikari
import tanjun
from utils.utils import *
from utils.ELO import *
from database import Database

component = tanjun.Component(name="matches module")


@component.with_slash_command
@tanjun.with_str_slash_option("result", "result", choices={"win":declares.WIN, "loss":declares.LOSS, "draw":declares.DRAW, "cancel":declares.CANCEL})
@tanjun.as_slash_command("declare", "declare a match's results", default_to_ephemeral=True, always_defer=True)
@ensure_registered
async def declare_match(ctx: tanjun.abc.SlashContext, result) -> None:

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

    response = "Declared " + str(result) + " for match " + str(match.name)

    #refresh match and check whether both declares are equal

    if match["p1_declared"] == match["p2_declared"]:
        new_outcome = declared_result

        if match["outcome"] != new_outcome:
            await update_match_outcome(ctx, match, new_outcome)
        else:
            response += "\nOutcome is already " + str(new_outcome)

    await ctx.edit_initial_response(response)

    DB.upsert_match(match)


@component.with_slash_command
@tanjun.with_str_slash_option("outcome", "set the outcome", choices={"1":results.PLAYER_1, "2":results.PLAYER_2, "draw":results.DRAW, "cancel":results.CANCEL})
@tanjun.with_str_slash_option("match_number", "Enter the match number")
@tanjun.as_slash_command("setmatch", "set a match's outcome", default_to_ephemeral=False, always_defer=True)
@ensure_registered
@ensure_staff
async def set_match_command(ctx: tanjun.abc.Context, match_number, outcome):

    DB = Database(ctx.guild_id)

    matches = DB.get_matches(match_id=match_number)
    if matches.empty:
        await ctx.edit_initial_response("No match found")
        return
    match = matches.iloc[0]

    if match["outcome"] == outcome:
        await ctx.edit_initial_response("Outcome is already " + str(outcome))
        return

    await update_match_outcome(ctx, match, outcome, staff_declared=outcome)
    await ctx.edit_initial_response("Match " + str(match.name) + " updated")



@component.with_slash_command
@tanjun.as_slash_command("match", "Your latest match's status", default_to_ephemeral=True, always_defer=True)
@ensure_registered
async def get_match(ctx: tanjun.abc.Context) -> None:

    DB = Database(ctx.guild_id)

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

    response_embed = Custom_Embed(type=Embed_Type.INFO, title=f"Match {str(match.name)} Outcome", description=f"{result}")

    await ctx.edit_initial_response(embed=response_embed)


async def update_match_outcome(ctx:tanjun.abc.Context, match, new_outcome, staff_declared=None, client=tanjun.injected(type=tanjun.abc.Client)):

    DB = Database(ctx.guild_id)

    p1 = DB.get_players(user_id=match["player_1"]).iloc[0]
    p2 = DB.get_players(user_id=match["player_2"]).iloc[0]

    #make sure this is the most recent match for both players
    p1_latest_match = DB.get_matches(user_id=p1["user_id"]).iloc[0]["match_id"]
    p2_latest_match = DB.get_matches(user_id=p2["user_id"]).iloc[0]["match_id"]

    if p1_latest_match != match.name or p2_latest_match != match.name:
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

        p1_matches = DB.get_matches(user_id=match["player_1"], number=Config.NUM_UNRANKED_MATCHES, from_first=True)

        print("p1_matches:", p1_matches)

        if len(p1_matches.index) >= Config.NUM_UNRANKED_MATCHES:
            p1_ranked_after = True

    if match["p2_is_ranked"]:
        p2_elo_after = match["p2_elo"] + standard_elo_change[1]
        p2_ranked_after = True
    else:
        p2_elo_after = match["p2_elo"] + standard_elo_change[1]*3 #temp

        p2_matches = DB.get_matches(user_id=match["player_2"], number=Config.NUM_UNRANKED_MATCHES, from_first=True)

        print("p2_matches", p2_matches)

        if len(p2_matches.index) >= Config.NUM_UNRANKED_MATCHES:
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

    result_embed = hikari.Embed(title="Match " + str(match.name) + " results: " + str(new_outcome), description="", color=Colors.PRIMARY)
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

    await client.rest.create_message(channel_id, embed=result_embed)


@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())