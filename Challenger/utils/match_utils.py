import alluka
import hikari
import tanjun
import re
import numpy as np

import time
import asyncio
import pandas as pd
from datetime import datetime

from Challenger.config import *
from .scoring import *
from .constants import *
from .style import *
from ..database import Guild_DB



def recalculate_matches(matches, match_id, new_outcome=None, updated_players=None, update_all=False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    starts from match_id and recalculates all matches after it.
    if new_starting_elo is set, it will update everyone's elo before any matches were played

    params:
        matches: a DataFrame of matches. must have index "match_id", and columns "p1_id", "p2_id", "p1_elo", "p2_elo", "p1_elo_after", "p2_elo_after", "p1_is_ranked", "p2_is_ranked", "p1_is_ranked_after", "p2_is_ranked_after", "outcome"
        match_id: the match id of the first match to be updated
        new_outcome: the new outcome of the match
        updated_players: pd.DataFrame of updated players. must have index user_id, columns "elo", "is_ranked"

    returns:
        updated_matches a DataFrame of the matches with updated prior and after elos and ranked status for each match affected by the outcome change.
        updated_players a DataFrame of each player's new elo and ranked status
    """

    matches = matches.copy()
    updated_players = updated_players.copy() if updated_players is not None else None

    if updated_players is None:
        updated_players = pd.DataFrame([], columns=["user_id", "elo", "is_ranked"]).set_index("user_id")

    match = matches.loc[match_id]

    p1_id = match["p1_id"]
    p2_id = match["p2_id"]

    #If this match should be affected in any way, calculate the players' new elos. If not, move on to the next match
    if p1_id in updated_players.index or p2_id in updated_players.index or new_outcome is not None or update_all:

        #By default their prior elo is what it is in the database. If it changed, update it

        p1_elo = matches.loc[match_id, "p1_elo"]
        p2_elo = matches.loc[match_id, "p2_elo"]

        for user_id, player in updated_players.iterrows():
            if user_id == p1_id:
                p1_elo = updated_players.loc[user_id, "elo"]
                matches.loc[match_id, "p1_elo"] = p1_elo

            if user_id == p2_id:
                p2_elo = updated_players.loc[user_id, "elo"]
                matches.loc[match_id, "p2_elo"] = p2_elo

        #New outcome
        outcome = match["outcome"]
        if new_outcome is not None:
            outcome = new_outcome
            matches.loc[match_id, "outcome"] = new_outcome

        #determine whether they're ranked based on the new outcome
        matches.loc[match_id, "p1_is_ranked"] = determine_is_ranked(matches, player_id=p1_id, latest_match_id=match_id-1)
        matches.loc[match_id, "p2_is_ranked"] = determine_is_ranked(matches, player_id=p2_id, latest_match_id=match_id-1)
        matches.loc[match_id, "p1_is_ranked_after"] = determine_is_ranked(matches, player_id=p1_id, latest_match_id=match_id)
        matches.loc[match_id, "p2_is_ranked_after"] = determine_is_ranked(matches, player_id=p2_id, latest_match_id=match_id)


        if matches.loc[match_id, "p1_is_ranked"]:
            p1_elo_after = p1_elo + calc_elo_change(p1_elo, p2_elo, outcome)[0]
        else:
            p1_elo_after = p1_elo + calc_prov_elo(p1_elo, p2_elo, outcome)[0]

        if matches.loc[match_id, "p2_is_ranked"]:
            p2_elo_after = p2_elo + calc_elo_change(p1_elo, p2_elo, outcome)[1]
        else:
            p2_elo_after = p2_elo + calc_prov_elo(p1_elo, p2_elo, outcome)[1]

        matches.loc[match_id, "p1_elo_after"] = p1_elo_after
        matches.loc[match_id, "p2_elo_after"] = p2_elo_after


        updated_players.loc[p1_id, "elo"] = p1_elo_after
        updated_players.loc[p2_id, "elo"] = p2_elo_after
        updated_players.loc[p1_id, "is_ranked"] = matches.loc[match_id, "p1_is_ranked_after"]
        updated_players.loc[p2_id, "is_ranked"] = matches.loc[match_id, "p2_is_ranked_after"]

    if match_id + 1 in matches.index:
        return recalculate_matches(matches=matches, match_id=match_id + 1, updated_players=updated_players, update_all=update_all)
    else:
        return matches, updated_players



def determine_is_ranked(all_matches, player_id, latest_match_id):
    """
        Counts all the matches the player has played in before the current match that weren't cancelled or undecided
        if they have played enough matches, they are ranked
    """

    player_matches = all_matches.loc[np.logical_or(all_matches["p1_id"] == player_id, all_matches["p2_id"] == player_id)]
    finished_matches = player_matches.loc[player_matches.index <= latest_match_id].loc[player_matches["outcome"].isin(Outcome.FINISHED)]

    return len(finished_matches) >= Elo.NUM_PLACEMENT_MATCHES



async def remove_from_q_timeout(ctx: tanjun.abc.Context, DB: Guild_DB):
    await asyncio.sleep(Config.QUEUE_JOIN_TIMEOUT)
    queue = DB.get_lobbies(channel_id=ctx.channel_id).iloc[0]  # would probably break if the channel was deleted after the player joined
    queue["player"] = None
    DB.upsert_lobby(queue)
    await ctx.respond("You have been removed from the queue")
    await ctx.get_channel().send("A player was removed from the queue after " + str(Config.QUEUE_JOIN_TIMEOUT // 60) + " minutes")


async def remove_from_queue(DB:Guild_DB, lobby):
    if lobby["player"] is None:
        return
    for i in asyncio.all_tasks():
        if i.get_name() == str(lobby["player"]) + str(lobby.name) + "_queue_timeout":
            i.cancel()
    lobby["player"] = None
    DB.upsert_lobby(lobby)


def describe_match(match: pd.Series, DB) -> hikari.Embed: # TODO take the match id

    p1_name = DB.get_players(user_id=match["p1_id"]).iloc[0]["username"]
    p2_name = DB.get_players(user_id=match["p2_id"]).iloc[0]["username"]

    def displayed_elo(elo, is_ranked):
        if elo is None:
            return "?"
        if is_ranked:
            return str(round(elo))
        else:
            return str(round(elo)) + "?"

    p1_prior_elo_displayed = displayed_elo(match["p1_elo"], match["p1_is_ranked"])
    p2_prior_elo_displayed = displayed_elo(match["p2_elo"], match["p2_is_ranked"])
    p1_after_elo_displayed = displayed_elo(match["p1_elo_after"], match["p1_is_ranked_after"])
    p2_after_elo_displayed = displayed_elo(match["p2_elo_after"], match["p2_is_ranked_after"])

    if match["outcome"] in Outcome.FINISHED:

        p1_elo_change = match["p1_elo_after"] - match["p1_elo"]
        p2_elo_change = match["p2_elo_after"] - match["p2_elo"]
        p1_elo_indicator = "???" if p1_elo_change > 0 else "???" if p1_elo_change < 0 else ""
        p2_elo_indicator = "???" if p2_elo_change > 0 else "???" if p2_elo_change < 0 else ""
        p1_elo_diff_str = str(round(abs(p1_elo_change)))
        p2_elo_diff_str = str(round(abs(p2_elo_change)))
        p1_elo_change_str = "> " + str(p1_prior_elo_displayed) + " -> **" + str(p1_after_elo_displayed) \
                            + "** *(" + p1_elo_indicator + p1_elo_diff_str + ")*\n"
        p2_elo_change_str = "> " + str(p2_prior_elo_displayed) + " -> **" + str(p2_after_elo_displayed) \
                            + "** *(" + p2_elo_indicator + p2_elo_diff_str + ")*\n"

    else:
        p1_elo_change_str = ""
        p2_elo_change_str = ""

    color = Colors.SUCCESS
    if match["outcome"] == Outcome.PLAYER_1:
        outcome_str = p1_name + " won"
    elif match["outcome"] == Outcome.PLAYER_2:
        outcome_str = p2_name + " won"
    elif match["outcome"] == Outcome.CANCEL:
        outcome_str = "Cancelled"
        color = Colors.DARK
    elif match["outcome"] == Outcome.DRAW:
        outcome_str = "Draw"
    else:
        outcome_str = "Undecided"
        color = Colors.WARNING

    if match["p1_declared"] == Outcome.PLAYER_1:
        p1_declared = "Declared win"
    elif match["p1_declared"] == Outcome.PLAYER_2:
        p1_declared = "Declared loss"
    elif match["p1_declared"] is None:
        p1_declared = "Didn't declare"
    else:
        p1_declared = match["p1_declared"]
    if match["p2_declared"] == Outcome.PLAYER_2:
        p2_declared = "Declared win"
    elif match["p2_declared"] == Outcome.PLAYER_1:
        p2_declared = "Declared loss"
    elif match["p2_declared"] is None:
        p2_declared = "Didn't declare"
    else:
        p2_declared = match["p2_declared"]


    embed = hikari.Embed(title="Match " + str(match.name), color=color)

    embed.add_field(name=outcome_str, value=BLANK)
    embed.add_field(name=str(p1_name), value=p1_elo_change_str + "> " + p1_declared, inline=True)
    embed.add_field(name="vs", value=BLANK, inline=True)
    embed.add_field(name=str(p2_name), value=p2_elo_change_str + "> " + p2_declared, inline=True)

    embed.set_footer(text=match["time_started"].strftime("%B %d, %Y, %H:%M") + " UTC")

    return embed



async def start_announce_new_match(ctx:tanjun.abc.Context, p1_info, p2_info):
    """creates a new match between the 2 players and announces it to the channel"""

    DB = Guild_DB(ctx.guild_id)

    p1_ping = "<@" + str(p1_info.name) + ">"
    p2_ping = "<@" + str(p2_info.name) + ">"

    p1_is_ranked = p1_info["is_ranked"]
    p2_is_ranked = p2_info["is_ranked"]

    new_match = DB.get_new_match()

    new_match[["time_started", "p1_id", "p2_id", "p1_elo", "p2_elo", "p1_is_ranked", "p2_is_ranked"]] = \
        [datetime.now(), p1_info.name, p2_info.name, p1_info["elo"], p2_info["elo"], p1_is_ranked, p2_is_ranked]

    DB.upsert_match(new_match)

    embed = hikari.Embed(title="Match " + str(new_match.name) + " started", description=p1_info["tag"] + " vs " + p2_info["tag"], color=Colors.PRIMARY)

    await ctx.get_channel().send(content=p1_ping+ " " + p2_ping, embed=embed, user_mentions=True)


async def announce_in_updates_channel(ctx, embed, client:tanjun.Client, content=None):
    DB = Guild_DB(ctx.guild_id)

    config = DB.get_config()
    channel_id = config["results_channel"]

    if channel_id is None:

        embed.set_footer(text="??? Announcing here because no match announcements channel is set. Type /config match-updates-channel to set one.")
        await ctx.get_channel().send(embed=embed)
        return
    await client.rest.create_message(channel_id, content=content, embed=embed, user_mentions=True)


async def update_players_elo_roles(ctx:tanjun.abc.Context, bot:hikari.GatewayBot, players:pd.DataFrame, role_ids=None):
    """
    Needs a message context to send an error message if the bot doesn't have role perms.
    players: dataframe with index user id and columns elo and is_ranked
    roles: list of role ids
    """

    DB = Guild_DB(ctx.guild_id)
    elo_roles = DB.get_elo_roles()
    if role_ids:
        elo_roles = elo_roles[elo_roles.index.isin(role_ids)]

    players_updated = 0

    try:
        for user_id, player in players.iterrows():

            players_updated += 1
            yield  "updating elo roles (" + str(round(100 * players_updated / players.shape[0])) + "%)"

            try:
                current_roles = (await ctx.rest.fetch_member(ctx.guild_id, user_id)).get_roles()
            except hikari.NotFoundError:
                continue

            current_roles = [role.id for role in current_roles]

            for role_id, role_info in elo_roles.iterrows():

                if not player["is_ranked"]:

                    if role_id in current_roles:
                        await bot.rest.remove_role_from_member(ctx.guild_id, user_id, role_id)

                    continue

                if role_info["min_elo"] <= player["elo"] <= role_info["max_elo"]:

                    if not role_id in current_roles:
                        await bot.rest.add_role_to_member(ctx.guild_id, user_id, role_id)

                else:
                    if role_id in current_roles:
                        await bot.rest.remove_role_from_member(ctx.guild_id, user_id, role_id)

    except hikari.ForbiddenError:
        await ctx.respond(embed=Custom_Embed(type=Embed_Type.ERROR, title="Unable to update roles", description="Please make sure the bot's role is above all elo roles"))

    yield "done"


def player_col_for_match(match, user_id, column, opponent=False): #useful probably

    if (match["p1_id"] == user_id) == (not opponent):

        return match["p1_" + column]
    elif (match["p2_id"] == user_id) == (not opponent):
        return match["p2_" + column]
    else:
        raise ValueError("Player not in match")

__all__ = ["describe_match", "announce_in_updates_channel", "update_players_elo_roles", "remove_from_q_timeout", "remove_from_queue",
           "recalculate_matches", "determine_is_ranked", "player_col_for_match", "start_announce_new_match"]