import hikari
import tanjun
import time

from datetime import datetime
import asyncio
import pandas as pd

from Challenger.helpers import *
from Challenger.database import *
from Challenger.config import *
from Challenger.utils import *

# from Challenger.utils import Outcome, Declare #dont need

from mongoengine.queryset.visitor import Q

#join the queue


@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.as_slash_command("join", "join the queue", default_to_ephemeral=True, always_defer=True)
async def join_q(ctx: tanjun.abc.Context, client:tanjun.Client=tanjun.injected(type=tanjun.Client)) -> None:


    # See who's in the queue for this lobby
    # if there is a player in the queue, check if they are the same person
    # if there's another player in the queue, create a new match


    guild = Guild.objects(guild_id=ctx.guild_id).first()

    #get the lobby and leaderboard for the channel
    leaderboard = None
    lobby = None
    for lb in guild.leaderboards:
        lobby = lb.lobbies.filter(channel_id=ctx.channel_id).first()
        if lobby:
            leaderboard = lb
            break

    if not lobby:
        await ctx.edit_initial_response("No lobby here")
        return

    player = Player.objects(guild_id=ctx.guild_id, user_id=ctx.author.id, leaderboard_name=leaderboard.name).first()
    if player is None:
        await ctx.edit_initial_response(f"Please register for {leaderboard.name}")
        return

    #check if player has finished their last match...

    await ctx.edit_initial_response(f"You silently joined the queue")

    if lobby.player_in_q is None:
        #create asyncio timeout
        lobby.player_in_q = player
        asyncio.create_task(remove_from_q_timeout(ctx.guild_id, leaderboard.name, ctx.channel_id, ctx),
                            name=get_timeout_name(ctx.guild_id, leaderboard.name, ctx.channel_id))

        await (await ctx.fetch_channel()).send("A player has joined the queue")

    else:

        if lobby.player_in_q == player:
            await ctx.edit_initial_response("You're already in the queue")
            return


        player1 = lobby.player_in_q.fetch()
        player2 = player

        remove_from_queue(ctx.guild_id, leaderboard.name, ctx.channel_id)

        await (await ctx.fetch_channel()).send("Queue is full. Creating match")

        # get both players by their user
        match = Match.objects(guild_id=Database.DEV_GUILD_ID, leaderboard_name="Ast").order_by("-match_id").first()
        if match is not None:
            new_match_id = match.match_id + 1
        else:
            new_match_id = 1

        match = Match(
            guild_id = ctx.guild_id,
            leaderboard_name = leaderboard.name,
            match_id=new_match_id,
            outcome=Outcome.PENDING,
            time_started=datetime.now(),

            player_1=player1,
            player_1_declared=Declare.UNDECIDED,
            player_1_elo=player1.rating,
            player_1_RD=player1.rating_deviation,

            player_2=player2,
            player_2_declared=Declare.UNDECIDED,
            player_2_elo=player2.rating,
            player_2_RD=player2.rating_deviation
        )
        match.save()

        embed = hikari.Embed(title="Match " + str(new_match_id) + " started",
                             description=str(player1.username) + " vs " + str(player2.username), color=Colors.PRIMARY)

        p1_ping = "<@" + str(player1.user_id) + ">"
        p2_ping = "<@" + str(player2.user_id) + ">"

        await ctx.get_channel().send(content=p1_ping + " " + p2_ping, embed=embed, user_mentions=True)

    guild.save()




#leave queue
@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.as_slash_command("leave", "leave the queue", default_to_ephemeral=True, always_defer=True)
async def leave_q(ctx: tanjun.abc.Context) -> None:

    guild = Guild.objects(guild_id=ctx.guild_id).first()

    # get the lobby and leaderboard for the channel
    leaderboard = None
    lobby = None
    for lb in guild.leaderboards:
        lobby = lb.lobbies.filter(channel_id=ctx.channel_id).first()
        if lobby:
            leaderboard = lb
            break

    if not lobby:
        await ctx.edit_initial_response("No lobby here")
        return

    if lobby.player_in_q is None or lobby.player_in_q.fetch().user_id != ctx.author.id:
        await ctx.edit_initial_response("You're not in the queue")
        return

    await remove_from_queue(ctx.guild_id, leaderboard.name, ctx.channel_id)
    await ctx.edit_initial_response("You left the queue")
    await (await ctx.fetch_channel()).send("A player has left the queue")
    guild.save()



@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.as_slash_command("queue", "queue status", default_to_ephemeral=True)
async def queue_status(ctx: tanjun.abc.Context) -> None:

    guild = Guild.objects(guild_id=ctx.guild_id).first()

    # get the lobby for the channel
    lobby = None
    for lb in guild.leaderboards:
        lobby = lb.lobbies.filter(channel_id=ctx.channel_id).first()
        if lobby:
            break

    if not lobby:
        await ctx.edit_initial_response("No lobby here")
        return


    # respond
    if lobby.player_in_q is None:
        await ctx.edit_initial_response("Queue is empty")
        return
    await ctx.edit_initial_response("One player is in the queue")



@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("outcome", "outcome", choices={"win":Declare.WIN, "loss":Declare.LOSS, "draw":Declare.DRAW, "cancel":Declare.CANCEL})
@tanjun.as_slash_command("declare", "declare a match's results", default_to_ephemeral=False, always_defer=True)
async def declare_match(ctx: tanjun.abc.SlashContext, outcome, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot), client=tanjun.injected(type=tanjun.abc.Client)) -> None:

    player_declared = outcome

    guild = Guild.objects(guild_id=ctx.guild_id).first()



    # get the leaderboard for the lobby
    leaderboard = None
    lobby = None
    for lb in guild.leaderboards:
        lobby = lb.lobbies.filter(channel_id=ctx.channel_id).first()
        if lobby:
            leaderboard = lb
            break

    if not lobby:
        await ctx.edit_initial_response("No lobby here")
        return

    player = Player.objects(guild_id=ctx.guild_id, leaderboard_name=leaderboard.name, user_id=ctx.author.id).first()
    if player is None:
        await ctx.edit_initial_response("Please register")
        return

    # get the most recent match player by this player in the leaderboard

    #player 1 or player 2 matches the player
    match = Match.objects(guild_id=ctx.guild_id, leaderboard_name=leaderboard.name).order_by('-match_id').filter(Q(player_1=player) | Q(player_2=player)).first()

    if match is None:
        await ctx.edit_initial_response("You played no matches")
        return

    if match.finalized:
        await ctx.edit_initial_response("Match is already finalized")
        return

    def desired_outcome(player, declare):
        return {
            Declare.WIN: Outcome.PLAYER_1 if player==1 else Outcome.PLAYER_2,
            Declare.LOSS: Outcome.PLAYER_2 if player==1 else Outcome.PLAYER_1,
            Declare.DRAW: Outcome.DRAW,
            Declare.CANCEL: Outcome.CANCELLED,
            Declare.UNDECIDED: Outcome.PENDING
        }[declare]


    player = 1 if match.player_1 == player else 2
    if match.outcome == desired_outcome(player, player_declared):
        await ctx.edit_initial_response(f"Outcome is already {match.outcome.value}")
        return

    if player == 1:
        match.player_1_declared = player_declared
    else:
        match.player_2_declared = player_declared

    if desired_outcome(1, match.player_1_declared) == desired_outcome(2, match.player_2_declared):

        #TODO Update the match, calculate elos, and announce results

        # get the relevant matches in a dataframe
        affected_matches = Match.objects(guild_id=ctx.guild_id, leaderboard_name=leaderboard.name, match_id__gte=match.match_id)

        df = pd.DataFrame([a.to_mongo() for a in affected_matches]).set_index("match_id").replace(np.nan, None)
        print(df)

        updated_matches, updated_players =  match_calculation.recalculate_matches(df, match.match_id, new_outcome=desired_outcome(2, match.player_1_declared))
        print(updated_matches)
        print(updated_players)

        # update the matches
        for index, m in updated_matches.iterrows():
            print(m)
            Match.objects(guild_id=ctx.guild_id, leaderboard_name=leaderboard.name, match_id=index).update(set__outcome=m['outcome'], set__player_1_elo=m['player_1_elo'], set__player_2_elo=m['player_2_elo'], set__player_1_RD=m['player_1_RD'], set__player_2_RD=m['player_2_RD'])




    match.save()
    guild.save()

    await ctx.respond("Outcome declared")






@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.with_user_slash_option("player", "whose matches to see (optional)", default=None)
@tanjun.with_user_slash_option("leaderboard", "which leaderboard to get the matches from", default=None)
@tanjun.as_slash_command("match-history", "All the match's results", default_to_ephemeral=True, always_defer=True)
async def match_history_cmd(ctx: tanjun.abc.Context, player, leaderboard, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot)) -> None:

    guild = Guild.objects(guild_id=ctx.guild_id).first()

    if leaderboard:
        lb = guild.leaderboards.filter(name=leaderboard).first()
        if lb is None:
            await ctx.edit_initial_response(f"No leaderboard named {leaderboard}")
            return
    else:
        lb = guild.leaderboards.first()




    matches_per_page = 5

    def get_matches_for_page(page_number):

        if page_number < 0:
            return None

        matches = Match.objects(guild_id=ctx.guild_id, leaderboard_name=lb.name).order_by('-match_id')[page_number*matches_per_page:(page_number+1)*matches_per_page]

        matches_df = pd.DataFrame([m.to_mongo() for m in matches]).set_index("match_id").replace(np.nan, None)


        if matches_df.index.size == 0:
            if page_number == 0: # no matches at all
                return [hikari.Embed(title="No matches to show", description=BLANK, color=Colors.PRIMARY)]
            return None

        embeds = []
        for match_id, match in matches_df.sort_index(ascending=True).iterrows():
            embed = describe_match(match)
            embeds.append(embed)

        return embeds


    await create_paginator(ctx, bot, get_matches_for_page, nextlabel="Older", prevlabel="Newer")



@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("outcome", "set the outcome", choices={"1":Outcome.PLAYER_1, "2":Outcome.PLAYER_2, "draw":Outcome.DRAW, "cancel":Outcome.CANCELLED}, default=None)
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
    matches = DB.get_matches()
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
    elif new_outcome == Outcome.CANCELLED:
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