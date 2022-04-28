import hikari
import tanjun
import time

from Challenger.helpers import *
from Challenger.database import *
from Challenger.config import *

import asyncio

import pandas as pd
# from Challenger.utils import Outcome, Declare #dont need



#join the queue


@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.as_slash_command("join", "join the queue", default_to_ephemeral=True, always_defer=True)
async def join_q(ctx: tanjun.abc.Context, client:tanjun.Client=tanjun.injected(type=tanjun.Client)) -> None:

    guild = Guild.objects(guild_id=ctx.guild_id).first()

    user = User.objects(user_id=ctx.author.id).first()

    #get the lobby and leaderboard for the channel
    leaderboard = None
    lobby = None
    for leaderboard in guild.leaderboards:
        lobby = leaderboard.lobbies.filter(channel_id=ctx.channel_id).first()
        if lobby:
            leaderboard = leaderboard
            break

    if not lobby:
        await ctx.edit_initial_response("No lobby here")
        return


    #get the player in the leaderboard
    player = None
    for player in leaderboard.players:
        if player.user.pk == user.id:
            player = player

    if player is None:
        await ctx.edit_initial_response(f"Please register for {leaderboard.name}")



    if lobby.user_in_q.pk == ctx.author.id:
        await ctx.edit_initial_response("You're already in the queue")
        return

    #check if player has finished their last match...

    if lobby.user_in_q is None:
        #create asyncio timeout
        lobby.user_in_q = user

        await ctx.edit_initial_response(f"You silently joined the queue")
        await (await ctx.fetch_channel()).send("A player has joined the queue")
    else:

        #cancel asyncio task
        opponent = lobby.user_in_q
        lobby.user_in_q = None

        await ctx.edit_initial_response("You silently joined the queue")
        await (await ctx.fetch_channel()).send("Queue is full. Creating match")

        # get both players by their user
        player1 = None
        player2 = None
        for player in leaderboard.players:
            if player.user.pk == user.id:
                player1 = player
            elif player.user.pk == opponent.id:
                player2 = player

        if player1 is None or player2 is None:
            raise Exception("Player not found") # TODO make this a util function

        new_match_id = 1
        if len(leaderboard.matches) > 0:
            new_match_id = leaderboard.matches[-1].match_id + 1

        match = Match(
            match_id=new_match_id,
            outcome=Outcome.PENDING,
            time_started=time.time(),

            player1_id=player1.user.pk,
            player1_declared=Declare.UNDECIDED,
            player1_elo=player1.rating,
            player1_RD=player1.rating_deviation,

            player2_id=player2.user.pk,
            player2_declared=Declare.UNDECIDED,
            player2_elo=player2.rating,
            player2_RD=player2.rating_deviation
        ) # TODO make this a util function

        leaderboard.matches.append(match)

    guild.save()







#leave queue
@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.as_slash_command("leave", "leave the queue", default_to_ephemeral=True, always_defer=True)
@ensure_registered
@get_channel_lobby
async def leave_q(ctx: tanjun.abc.Context, lobby) -> None:

    DB = Guild_DB(ctx.guild_id)
    player_id = ctx.author.id

    if lobby["player"] == player_id:
        await remove_from_queue(DB, lobby)
        await ctx.edit_initial_response("Left the queue")
        await (await ctx.fetch_channel()).send("A player has left the queue")
    else:
        await ctx.edit_initial_response("You're not in the queue")




@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.as_slash_command("queue", "queue status", default_to_ephemeral=True)
@get_channel_lobby
async def queue_status(ctx: tanjun.abc.Context, lobby) -> None:
    if lobby["player"]:
        await ctx.edit_initial_response("1 player in queue")
    else:
        await ctx.edit_initial_response("Queue is empty")



@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("result", "result", choices={"win":Declare.WIN, "loss":Declare.LOSS, "draw":Declare.DRAW, "cancel":Declare.CANCEL})
@tanjun.as_slash_command("declare", "declare a match's results", default_to_ephemeral=False, always_defer=True)
@ensure_registered
async def declare_match(ctx: tanjun.abc.SlashContext, result, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot),client=tanjun.injected(type=tanjun.abc.Client)) -> None:

    DB = Guild_DB(ctx.guild_id)

    matches = DB.get_matches(user_id=ctx.author.id)
    if matches.empty:
        await ctx.edit_initial_response("You haven't played a match")
        return
    match = matches.iloc[0]


    if match["outcome"] == result:
        await ctx.edit_initial_response("Outcome is already " + str(result))
        return

    #check if result was declared by staf
    if match["staff_declared"]:
        await ctx.edit_initial_response("Staff already finalized this match's result")
        return

    #set the player's declared result in the match
    is_p1 = match["p1_id"] == ctx.author.id
    declare_to_result = {
        Declare.WIN: Outcome.PLAYER_1 if is_p1 else Outcome.PLAYER_2,
        Declare.LOSS: Outcome.PLAYER_2 if is_p1 else Outcome.PLAYER_1,
        Declare.DRAW: Outcome.DRAW,
        Declare.CANCEL: Outcome.CANCEL
    }
    new_outcome = declare_to_result[result]
    if is_p1:
        match["p1_declared"] = new_outcome
    else:
        match["p2_declared"] = new_outcome

    #update the match in the database
    DB.upsert_match(match)

    await ctx.respond("Declared " + str(result) + " for match " + str(match.name))

    #check whether both declares match
    if match["p1_declared"] == match["p2_declared"]:
        updated_players_embed, num_updated = await update_match_result(ctx, match.name, new_outcome, bot=bot)

        if num_updated > 2:
            await announce_in_updates_channel(ctx, updated_players_embed, client)

        match = DB.get_matches(match_id=match.name).iloc[0]
        match_embed = describe_match(match, DB)
        await announce_in_updates_channel(ctx, match_embed, client=client)



@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.with_user_slash_option("player", "whose matches to see (optional)", default=None)
@tanjun.as_slash_command("match-history", "All the match's results", default_to_ephemeral=True, always_defer=True)
@ensure_registered
async def match_history_cmd(ctx: tanjun.abc.Context, player, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot)) -> None:

    DB = Guild_DB(ctx.guild_id)

    user_id = player.channel_id if player else None

    matches_per_page = 5

    def get_matches_for_page(page_number):

        if page_number < 0:
            return None

        matches = DB.get_matches(user_id=user_id, limit=matches_per_page, chronological=False, skip=page_number * matches_per_page)

        if matches.index.size == 0:
            if page_number == 0: # no matches at all
                return [hikari.Embed(title="No matches to show", description=BLANK, color=Colors.PRIMARY)]
            return None

        embeds = []
        for match_id, match in matches.sort_index(ascending=True).iterrows():
            embed = describe_match(match, DB)
            embeds.append(embed)

        return embeds



    await create_paginator(ctx, bot, get_matches_for_page, nextlabel="Older", prevlabel="Newer")



@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("outcome", "set the outcome", choices={"1":Outcome.PLAYER_1, "2":Outcome.PLAYER_2, "draw":Outcome.DRAW, "cancel":Outcome.CANCEL}, default=None)
@tanjun.with_user_slash_option("winner", "set the winner (optional)", default=None)
@tanjun.with_str_slash_option("match_number", "Enter the match number")
@tanjun.as_slash_command("setmatch", "set a match's outcome", default_to_ephemeral=False, always_defer=True)
@ensure_staff
@ensure_registered
async def set_match(ctx: tanjun.abc.Context, match_number, winner, outcome, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot), client:tanjun.abc.Client=tanjun.injected(type=tanjun.abc.Client)):

    DB = Guild_DB(ctx.guild_id)

    matches = DB.get_matches(match_id=match_number)
    if matches.empty:
        await ctx.edit_initial_response("No match found")
        return
    match = matches.iloc[0]

    if winner:
        winner_id = winner.channel_id
        if winner_id == match["p1_id"]:
            new_outcome = Outcome.PLAYER_1
        elif winner_id == match["p2_id"]:
            new_outcome = Outcome.PLAYER_2
        else:
            await ctx.edit_initial_response("This player is not in this match")
            return
    elif outcome:
        if match["outcome"] == outcome:
            return await ctx.edit_initial_response("Outcome is already " + str(outcome))
        new_outcome = outcome
    else:
        return await ctx.edit_initial_response("Specify an outcome")


    updated_players_embed, num_updated = await update_match_result(ctx, match.name, new_outcome, bot=bot, staff_declared=True)

    if num_updated > 2:
        await announce_in_updates_channel(ctx, updated_players_embed, client)

    match = DB.get_matches(match_id=match.name).iloc[0]
    match_embed = describe_match(match, DB)
    await announce_in_updates_channel(ctx, match_embed, client=client)

    await ctx.respond("Match updated")



async def update_match_result(ctx:tanjun.abc.Context, match_id, new_outcome, bot:hikari.GatewayBot, staff_declared=None):
    """
    updates a match's result, and returns an embed listing all players whose elo was updated and the number of players updated
    """

    DB = Guild_DB(ctx.guild_id)
    matches = DB.get_matches() #TODO dont get all the matches at once
    match = matches.loc[match_id]

    if staff_declared:
        matches.loc[match_id, "staff_declared"] = new_outcome

    start_time = time.time()
    matches_updated, players_after = recalculate_matches(matches, match.name, new_outcome)
    print("Updated " + str(matches_updated.index.size) + " matches in", time.time() - start_time) #measure time
    DB.upsert_matches(matches_updated)

    players = DB.get_players(user_ids=list(players_after.index))
    players_before = players.loc[players_after.index, players_after.columns]
    players[players_after.columns] = players_after
    DB.upsert_players(players)

    print(players_after, "\n", players_before)

    # filter out players whose elo hasn't changed much
    eq_threshhold = Elo.K / 100
    mask = abs(players_before["elo"]-players_after["elo"]).gt(eq_threshhold)
    players_before = players_before.loc[mask]
    players_after = players.loc[mask]

    # announce the updated match in the match announcements channel
    updated_players_str = ""
    for user_id, updated_player in players_after.iterrows():

        prior_elo_str = str(round(players_before.loc[user_id, "elo"]))
        if not players_before.loc[user_id, "is_ranked"]:
            prior_elo_str += "?"

        updated_elo_str = str(round(updated_player["elo"]))
        if not updated_player["is_ranked"]:
            updated_elo_str += "?"

        updated_players_str += "<@" + str(user_id) + "> " + prior_elo_str + " -> " + updated_elo_str + "\n"

    async for message in update_players_elo_roles(ctx, bot, players_after):
        pass

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

    embed = hikari.Embed(title="Match " + str(match_id) + " Updated: **" + displayed_outcome + "**", description=updated_players_str, color=Colors.PRIMARY)

    if staff_declared:
        embed.add_field(name="Result overriden by staff", value=f"(Set by {ctx.author.username}#{ctx.author.discriminator})")

    return embed, len(players_after.index)



matches = tanjun.Component(name="matches", strict=True).load_from_scope().make_loader()