import hikari
import tanjun
import time

from Challenger.utils import *
from Challenger.database import Session
from Challenger.config import *


from Challenger.utils import Outcome, Declare #dont need




@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("result", "result", choices={"win":Declare.WIN, "loss":Declare.LOSS, "draw":Declare.DRAW, "cancel":Declare.CANCEL})
@tanjun.as_slash_command("declare", "declare a match's results", default_to_ephemeral=False, always_defer=True)
@ensure_registered
async def declare_match(ctx: tanjun.abc.SlashContext, result, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot),client=tanjun.injected(type=tanjun.abc.Client)) -> None:

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
        return await update_announce_match_outcome(ctx, match.name, new_outcome, bot=bot, client=client)


@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_user_slash_option("player", "optional: enter whose matches to get", default=None)
@tanjun.as_slash_command("match-history", "All the match's results", default_to_ephemeral=True, always_defer=True)
@ensure_registered
async def match_history_cmd(ctx: tanjun.abc.Context, player, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot)) -> None:

    response = await ctx.fetch_initial_response()

    DB = Session(ctx.guild_id)

    user_id = player.id if player else None

    matches_per_page = 5

    def get_matches_for_page(page_number):

        if page_number < 0:
            return None

        matches = DB.get_matches(user_id=user_id, limit=matches_per_page, increasing=False, skip=page_number * matches_per_page)

        if matches.index.size == 0:
            if page_number == 0:
                # no matches at all
                return [hikari.Embed(title="No matches to show", description="*_ _*", color=Colors.PRIMARY)]
            return None

        embeds = []
        for match_id, match in matches.sort_index(ascending=True).iterrows():
            embed = describe_match(match, DB)
            embeds.append(embed)

        return embeds


    await create_paginator(ctx, bot, response, get_matches_for_page, nextlabel="Older", prevlabel="More recent")



@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("outcome", "set the outcome", choices={"1":Outcome.PLAYER_1, "2":Outcome.PLAYER_2, "draw":Outcome.DRAW, "cancel":Outcome.CANCEL})
@tanjun.with_str_slash_option("match_number", "Enter the match number")
@tanjun.as_slash_command("setmatch", "set a match's outcome", default_to_ephemeral=False, always_defer=True)
@ensure_staff
@ensure_registered
async def set_match(ctx: tanjun.abc.Context, match_number, outcome, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot), client:tanjun.abc.Client=tanjun.injected(type=tanjun.abc.Client)):

    DB = Session(ctx.guild_id)

    matches = DB.get_matches(match_id=match_number)
    if matches.empty:
        await ctx.edit_initial_response("No match found")
        return
    match = matches.iloc[0]

    return await update_announce_match_outcome(ctx, match.name, outcome, bot=bot, client=client, staff_declared=True)



async def update_announce_match_outcome(ctx:tanjun.abc.Context, match_id, new_outcome, bot:hikari.GatewayBot, client:tanjun.Client, staff_declared=None):

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

    start_time = time.time()
    updated_matches, updated_players = update_matches(matches, match.name, new_outcome)
    print("Updated " + str(updated_matches.index.size) + " matches in", time.time() - start_time)
    DB.upsert_matches(updated_matches)

    players = DB.get_players(user_ids=list(updated_players.index))
    players_before = players.loc[updated_players.index, updated_players.columns]
    players[updated_players.columns] = updated_players
    DB.upsert_players(players)


    # announce the updated match in the match announcements channel
    updated_players_str = ""

    for id, row in updated_players.iterrows():
        prior_elo_str = str(round(players_before.loc[id, "elo"]))
        if not players_before.loc[id, "is_ranked"]:
            prior_elo_str += "?"

        updated_elo_str = str(round(updated_players.loc[id, "elo"]))
        if not updated_players.loc[id, "is_ranked"]:
            updated_elo_str += "?"

        updated_players_str += "<@" + str(id) + "> " + prior_elo_str + " -> " + updated_elo_str + "\n"
        await update_player_elo_roles(ctx, bot, id)

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
    embed.add_field(name="Updated Elo", value=updated_players_str)

    if staff_declared:
        embed.add_field(name="Result overriden by staff", value=f"(Set by {ctx.author.username}#{ctx.author.discriminator})")

    await announce_as_match_update(ctx, embed, client)



matches = tanjun.Component(name="matches", strict=True).load_from_scope().make_loader()