import hikari
import tanjun
import pandas as pd
import numpy as np

from hikari.interactions.base_interactions import ResponseType

from Challenger.utils import *
from Challenger.database import Session
from Challenger.config import Config



@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("result", "result", choices={"win":Declare.WIN, "loss":Declare.LOSS, "draw":Declare.DRAW, "cancel":Declare.CANCEL})
@tanjun.as_slash_command("declare", "declare a match's results", default_to_ephemeral=False, always_defer=True)
@ensure_registered
async def declare_match(ctx: tanjun.abc.SlashContext, result, client=tanjun.injected(type=tanjun.abc.Client)) -> None:

    DB = Session(ctx.guild_id)

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
        Declare.WIN: Outcome.PLAYER_1 if is_p1 else Outcome.PLAYER_2,
        Declare.LOSS: Outcome.PLAYER_2 if is_p1 else Outcome.PLAYER_1,
        Declare.DRAW: Outcome.DRAW,
        Declare.CANCEL: Outcome.CANCEL
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


@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_user_slash_option("player", "optional: enter whose matches to get", default=None)
@tanjun.as_slash_command("match-history", "All the match's results", default_to_ephemeral=True, always_defer=True)
@ensure_registered
async def match_history_cmd(ctx: tanjun.abc.Context, player, bot=tanjun.injected(type=hikari.GatewayBot)) -> None:

    response = await ctx.fetch_initial_response()

    DB = Session(ctx.guild_id)

    user_id = player.id if player else None

    matches_per_page = 2

    matches = DB.get_matches(user_id=ctx.author.id, number=matches_per_page).sort_index(ascending=True) #5 matches per page

    def get_embeds_for_page(page_number):
        matches = DB.get_matches(user_id=user_id, number=matches_per_page, increasing=False, skip=page_number*matches_per_page)

        embeds = []

        for match_id, match in matches.iterrows():
            embed = describe_match(match)
            embeds.append(embed)

        return embeds



    if matches.empty:
        await ctx.respond("you haven't played any matches")
        return

    embeds = []

    for match_id, match in matches.iterrows():
        embeds.append(describe_match(match, DB))

    await ctx.edit_initial_response(embeds=embeds)

    page_navigator = ctx.rest.build_action_row()
    page_navigator.add_button(hikari.messages.ButtonStyle.PRIMARY, "Older").set_label("Older").set_emoji("⬅️").add_to_container()
    page_navigator.add_button(hikari.messages.ButtonStyle.PRIMARY, "More recent").set_label("More recent").set_emoji("➡️").add_to_container()

    await ctx.edit_initial_response(embeds=embeds, components=[page_navigator])

    cur_page = 0


    with bot.stream(hikari.InteractionCreateEvent, timeout=Config.DEFAULT_TIMEOUT).filter(
                ("interaction.type", hikari.interactions.InteractionType.MESSAGE_COMPONENT),
                ("interaction.user.id", ctx.author.id),
                ("interaction.message.id", response.id)) as stream:
        async for event in stream:
            await event.interaction.create_initial_response(ResponseType.DEFERRED_MESSAGE_UPDATE)
            if event.interaction.custom_id == "Older":
                cur_page -= 1
            elif event.interaction.custom_id == "More recent":
                cur_page += 1

            embeds = get_embeds_for_page(cur_page)
            prev_page_exists = cur_page >= 0
            next_page_exists = len(get_embeds_for_page(cur_page+1)) > 0
            print(next_page_exists)

            await ctx.edit_initial_response(embeds=embeds, components=[page_navigator])


@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("outcome", "set the outcome", choices={"1":Outcome.PLAYER_1, "2":Outcome.PLAYER_2, "draw":Outcome.DRAW, "cancel":Outcome.CANCEL})
@tanjun.with_str_slash_option("match_number", "Enter the match number")
@tanjun.as_slash_command("setmatch", "set a match's outcome", default_to_ephemeral=False, always_defer=True)
@ensure_staff
@ensure_registered
async def set_match(ctx: tanjun.abc.Context, match_number, outcome, client=tanjun.injected(type=tanjun.abc.Client)):

    DB = Session(ctx.guild_id)

    matches = DB.get_matches(match_id=match_number)
    if matches.empty:
        await ctx.edit_initial_response("No match found")
        return
    match = matches.iloc[0]

    return await set_match_outcome(ctx, match.name, outcome, client, staff_declared=True)


def get_provisional_game_results(all_matches, player_id, latest_match_id): #TODO: support draws

    player_matches = all_matches.loc[np.logical_or(all_matches["p1_id"] == player_id, all_matches["p2_id"] == player_id)]
    player_matches = player_matches.loc[player_matches.index <= latest_match_id]

    results = []

    for match_id, match in player_matches.iterrows():
        if match["outcome"] == Outcome.CANCEL or match["outcome"] == Outcome.DRAW or match["outcome"] == Outcome.UNDECIDED or match["outcome"] is None:
            continue

        if match["p1_id"] == player_id:
            winning_outcome = Outcome.PLAYER_1
            opponent_elo = match["p2_elo"]
        else:
            winning_outcome = Outcome.PLAYER_2
            opponent_elo = match["p1_elo"]

        if match["outcome"] == winning_outcome:
            results.append(("win", opponent_elo))
        else:
            results.append(("loss", opponent_elo))

    return results


def determine_is_ranked(all_matches, player_id, latest_match_id):
    """
        Counts all the matches the player has played in before the current match that weren't cancelled or undecided
        if they have played enough matches, they are ranked
    """
    player_matches = all_matches.loc[np.logical_or(all_matches["p1_id"] == player_id, all_matches["p2_id"] == player_id)]
    player_matches = player_matches.loc[player_matches.index <= latest_match_id]\
    .loc[np.logical_or(player_matches["outcome"] == Outcome.PLAYER_1, player_matches["outcome"] == Outcome.PLAYER_2, player_matches["outcome"] == Outcome.DRAW)]

    return len(player_matches) >= scoring.NUM_UNRANKED_MATCHES


def calculate_new_elos(matches, match_id, new_outcome=None, _updated_players=None):
    """
    params:
        matches: a DataFrame of matches. must have columns "p1_id", "p2_id", "p1_elo", "p2_elo", "p1_is_ranked", "p2_is_ranked", "outcome"
        match_id: the match id of the match to be updated
        new_outcome: the new outcome of the match

    returns:
        a DataFrame of the matches with updated prior and after elos and ranked status for each match affected by the outcome change.
        a DataFrame of each player's new elo and ranked status
    """

    if _updated_players is None:
        _updated_players = pd.DataFrame([], columns=["user_id", "elo", "is_ranked"]).set_index("user_id")

    match = matches.loc[match_id]

    p1_id = match["p1_id"]
    p2_id = match["p2_id"]

    #If this match should be affected in any way, calculate the players' new elos. If not, move on to the next match
    if p1_id in _updated_players.index or p2_id in _updated_players.index or new_outcome is not None:

        #By default their prior elo is what it is in the database. If it changed, update it
        p1_elo = match["p1_elo"]
        p2_elo = match["p2_elo"]
        for user_id, player in _updated_players.iterrows():
            if user_id == p1_id:
                p1_elo = _updated_players.loc[user_id, "elo"]
                matches.loc[match_id, "p1_elo"] = p1_elo

            if user_id == p2_id:
                p2_elo = _updated_players.loc[user_id, "elo"]
                matches.loc[match_id, "p2_elo"] = p2_elo

        outcome = match["outcome"]
        if new_outcome is not None:
            outcome = new_outcome
            matches.loc[match_id, "outcome"] = new_outcome

        if matches.loc[match_id, "p1_is_ranked"]:
            p1_elo_after = p1_elo + calc_elo_change(p1_elo, p2_elo, outcome)[0]
        else:
            p1_elo_after = p1_elo + calc_prov_elo(p1_elo, p2_elo, outcome)[0]

        if matches.loc[match_id, "p2_is_ranked"]:
            p2_elo_after = p2_elo + calc_elo_change(p2_elo, p1_elo, outcome)[1]
        else:
            p2_elo_after = p2_elo + calc_prov_elo(p2_elo, p1_elo, outcome)[1]

        matches.loc[match_id, "p1_elo_after"] = p1_elo_after
        matches.loc[match_id, "p2_elo_after"] = p2_elo_after

        #determine whether they're ranked based on the updated matches before this one
        matches.loc[match_id, "p1_is_ranked"] = determine_is_ranked(matches, player_id=p1_id, latest_match_id=match_id-1)
        matches.loc[match_id, "p2_is_ranked"] = determine_is_ranked(matches, player_id=p2_id, latest_match_id=match_id-1)
        matches.loc[match_id, "p1_is_ranked_after"] = determine_is_ranked(matches, player_id=p1_id, latest_match_id=match_id)
        matches.loc[match_id, "p2_is_ranked_after"] = determine_is_ranked(matches, player_id=p2_id, latest_match_id=match_id)

        _updated_players.loc[p1_id, "elo"] = p1_elo_after
        _updated_players.loc[p2_id, "elo"] = p2_elo_after
        _updated_players.loc[p1_id, "is_ranked"] = matches.loc[match_id, "p1_is_ranked_after"]
        _updated_players.loc[p2_id, "is_ranked"] = matches.loc[match_id, "p2_is_ranked_after"]


    # do the same to the next match
    if matches[match_id+1:].empty:
        return matches, _updated_players
    else:
        return calculate_new_elos(matches, match_id + 1, _updated_players=_updated_players)


async def set_match_outcome(ctx:tanjun.abc.Context, match_id, new_outcome, client:tanjun.abc.Client=tanjun.injected(type=tanjun.abc.Client), staff_declared=None):

    DB = Session(ctx.guild_id)
    matches = DB.get_matches() #TODO dont get all the matches at once
    match = matches.loc[match_id]

    try:
        p1 = DB.get_players(user_id=match["p1_id"]).iloc[0]
        p2 = DB.get_players(user_id=match["p2_id"]).iloc[0]
    except IndexError:
        return await ctx.respond(embed=Custom_Embed(type=Embed_Type.ERROR, description="One of the players in this match doesn't exist anymore"))

    if match["outcome"] == new_outcome:
        return await ctx.edit_initial_response("Outcome is already " + str(new_outcome))

    if staff_declared:
        matches.loc[match_id, "staff_declared"] = new_outcome

    updated_matches, updated_players = calculate_new_elos(matches.copy(), match.name, new_outcome)

    DB.upsert_matches(updated_matches)

    players = DB.get_players(user_ids=list(updated_players.index))
    players[updated_players.columns] = updated_players
    DB.upsert_players(players)


    # announce the updated match in the match announcements channel
    updated_players_message = ""
    players_before = players.loc[updated_players.index, updated_players.columns]

    for index, row in updated_players.iterrows():
        displayed_prior_elo = str(round(players_before.loc[index, "elo"]))
        if not players_before.loc[index, "is_ranked"]:
            displayed_prior_elo += "?"

        displayed_updated_elo = str(round(updated_players.loc[index, "elo"]))
        if not updated_players.loc[index, "is_ranked"]:
            displayed_updated_elo += "?"

        updated_players_message += "<@" + str(index) + "> " + displayed_prior_elo + " -> " + displayed_updated_elo + "\n"

    if new_outcome == Outcome.PLAYER_1: #refactor this
        winner_id = match["p1_id"]
        displayed_outcome = str(DB.get_players(user_id=winner_id).iloc[0]["username"]) + " won"
    elif new_outcome == Outcome.PLAYER_2:
        winner_id = match["p2_id"]
        displayed_outcome = str(DB.get_players(user_id=winner_id).iloc[0]["username"]) + " won"
    elif new_outcome == Outcome.CANCEL:
        displayed_outcome = "Cancelled"
    elif new_outcome == Outcome.DRAW:
        displayed_outcome = "Draw"
    else:
        displayed_outcome = "Ongoing" #undecided, or ongoing

    embed = Custom_Embed(type=Embed_Type.INFO, title="Match " + str(match_id) + " Updated: **" + displayed_outcome + "**", description="*_ _*")
    embed.add_field(name="Updated Elo", value=updated_players_message)

    if staff_declared:
        embed.add_field(name="Result overriden by staff", value=f"(Set by {ctx.author.username}#{ctx.author.discriminator})")


    config = DB.get_config()
    channel_id = config["results_channel"]

    if channel_id is None:
        await ctx.get_channel().send("\nNo match announcements channel specified. Announcing here", embed=embed)
        return
    await client.rest.create_message(channel_id, embed=embed)



matches = tanjun.Component(name="matches", strict=True).load_from_scope().make_loader()