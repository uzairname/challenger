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
        # get the relevant matches in a dataframe
        affected_matches = Match.objects(guild_id=ctx.guild_id, leaderboard_name=leaderboard.name, match_id__gte=match.match_id)
        affected_matches_df = pd.DataFrame([a.to_mongo() for a in affected_matches]).set_index("match_id").replace(np.nan, None)

        updated_matches, updated_players =  match_calculation.recalculate_matches(affected_matches_df, match.match_id, new_outcome=desired_outcome(1, match.player_1_declared))

        # update the matches
        for index, m in updated_matches.iterrows():
            Match.objects(guild_id=ctx.guild_id, leaderboard_name=leaderboard.name, match_id=index).update(set__outcome=m['outcome'], set__player_1_elo=m['player_1_elo'], set__player_2_elo=m['player_2_elo'], set__player_1_RD=m['player_1_RD'], set__player_2_RD=m['player_2_RD'])

        # update the players
        for index, p in updated_players.iterrows():
            Player.objects(guild_id=ctx.guild_id, leaderboard_name=leaderboard.name, user_id=index).update(set__elo=p['elo'], set__RD=p['RD'])


    match.save()
    guild.save()

    await ctx.respond("Outcome declared")






@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.with_user_slash_option("player", "whose matches to see (optional)", default=None)
@tanjun.with_str_slash_option("leaderboard", "which leaderboard to get the matches from", default=None)
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


        if len(matches) == 0:
            if page_number == 0: # no matches at all
                return [hikari.Embed(title="No matches to show", description=BLANK, color=Colors.PRIMARY)]
            return None

        start_time = time.time()
        matches_df = pd.DataFrame([m.to_mongo() for m in matches]).set_index("match_id").replace(np.nan, None)
        print(f"{time.time() - start_time} seconds to get matches df")

        embeds = []
        for match_id, match in matches_df.sort_index(ascending=True).iterrows():
            embed = describe_match(match)
            embeds.append(embed)

        return embeds

    await create_paginator(ctx, bot, get_matches_for_page, nextlabel="Older", prevlabel="Newer")



@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("outcome", "set the outcome", choices={"1":Outcome.PLAYER_1, "2":Outcome.PLAYER_2, "draw":Outcome.DRAW, "cancel":Outcome.CANCELLED}, default=None)
# @tanjun.with_user_slash_option("winner", "set the winner (optional)", default=None)
@tanjun.with_int_slash_option("match_number", "Enter the match number")
@tanjun.with_str_slash_option("leaderboard", "which leaderboard", default=None)
@tanjun.as_slash_command("setmatch", "set a match's outcome", default_to_ephemeral=False, always_defer=True)
async def set_match(ctx: tanjun.abc.Context, leaderboard, match_number, outcome, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot)):

    leaderboard_name = leaderboard

    leaderboards = Guild.objects(guild_id=ctx.guild_id).first().leaderboards

    if leaderboard_name is None:
        leaderboard = leaderboards.first()
    else:
        leaderboard = leaderboards.filter(name=leaderboard_name).first()

    affected_matches = Match.objects(guild_id=ctx.guild_id, leaderboard_name=leaderboard.name, match_id__gte=match_number)

    if len(affected_matches) == 0:
        await ctx.edit_initial_response(f"No matches found")
        return

    df = pd.DataFrame([a.to_mongo() for a in affected_matches]).set_index("match_id").replace(np.nan, None)

    updated_matches, updated_players = match_calculation.recalculate_matches(df, match_number, new_outcome=outcome)

    # update the players
    for player_id, p in updated_players.iterrows():
        Player.objects.with_id(player_id).update(set__elo=p['elo'], set__RD=p['RD'])

    # update the matches
    for match_id, m in updated_matches.iterrows():
        Match.objects(guild_id=ctx.guild_id, leaderboard_name=leaderboard.name, match_id=match_id).update(
            set__outcome=m['outcome'], set__player_1_elo=m['player_1_elo'], set__player_2_elo=m['player_2_elo'],
            set__player_1_RD=m['player_1_RD'], set__player_2_RD=m['player_2_RD'])


    updated_players_strs = []
    for player_id, player in updated_players.iterrows():
        updated_elo_str = str(round(player["elo"]))
        updated_players_strs.append(
            "<@" + str(player["user_id"]) + "> -> " + updated_elo_str + "\n")


    def get_updated_players_for_page(page_num):
        page_size = 10
        start_index = page_size * page_num
        end_index = start_index + page_size

        if page_num < 0:
            return None

        if end_index > len(updated_players_strs):
            end_index = len(updated_players_strs)

        if start_index >= end_index:
            return None

        embed = hikari.Embed(title="updated elo", description=''.join(updated_players_strs[start_index:end_index]), color=Colors.PRIMARY)
        return embed


    await create_paginator(ctx, bot, get_updated_players_for_page)
    pass



matches = tanjun.Component(name="matches", strict=True).load_from_scope().make_loader()