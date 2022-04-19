import hikari
import tanjun
import re
import numpy as np
from datetime import datetime
import asyncio
import pandas as pd
from Challenger.config import *

from .scoring import *
from .style import *
from ..database import Session



def update_matches(matches, match_id, new_outcome=None, _updated_players=None): #TODO make unit test
    """
    params:
        matches: a DataFrame of matches. must index "match_id", and columns "p1_id", "p2_id", "p1_elo", "p2_elo", "p1_elo_after", "p2_elo_after", "p1_is_ranked", "p2_is_ranked", "p1_is_ranked_after", "p2_is_ranked_after", "outcome"
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
        p1_elo = matches.loc[match_id, "p1_elo"]
        p2_elo = matches.loc[match_id, "p2_elo"]
        for user_id, player in _updated_players.iterrows():
            if user_id == p1_id:
                p1_elo = _updated_players.loc[user_id, "elo"]
                matches.loc[match_id, "p1_elo"] = p1_elo

            if user_id == p2_id:
                p2_elo = _updated_players.loc[user_id, "elo"]
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


        _updated_players.loc[p1_id, "elo"] = p1_elo_after
        _updated_players.loc[p2_id, "elo"] = p2_elo_after
        _updated_players.loc[p1_id, "is_ranked"] = matches.loc[match_id, "p1_is_ranked_after"]
        _updated_players.loc[p2_id, "is_ranked"] = matches.loc[match_id, "p2_is_ranked_after"]

        if match_id + 1 in matches.index:
            return update_matches(matches=matches, match_id=match_id + 1, _updated_players=_updated_players)
        else:
            return matches, _updated_players



def determine_is_ranked(all_matches, player_id, latest_match_id):
    """
        Counts all the matches the player has played in before the current match that weren't cancelled or undecided
        if they have played enough matches, they are ranked
    """

    player_matches = all_matches.loc[np.logical_or(all_matches["p1_id"] == player_id, all_matches["p2_id"] == player_id)]
    player_matches = player_matches.loc[player_matches.index <= latest_match_id]\
    .loc[np.logical_or(player_matches["outcome"] == Outcome.PLAYER_1, player_matches["outcome"] == Outcome.PLAYER_2, player_matches["outcome"] == Outcome.DRAW)]

    return len(player_matches) >= Elo.NUM_UNRANKED_MATCHES



class InputParser():

    def __init__(self, input_string):

        text_pat = r"[a-zA-Z\d\s]+"

        channel_pat = r"<#(\d{17,19})>"
        role_pat = r"<@&(\d{17,19})>"
        user_pat = r"<@!?(\d{17,19})>"

        name = re.match(text_pat, input_string)
        if name:
            name = name[0].strip()

        self.channels = np.array(re.findall(channel_pat, input_string)).astype("int64")
        self.roles = np.array(re.findall(role_pat, input_string)).astype("int64")
        self.users = np.array(re.findall(user_pat, input_string)).astype("int64")
        self.text = name

    def describe(self):

        description = ""
        if self.text:
            description += "\nName:\n> " + str(self.text)

        if self.channels.size > 0:
            description += "\nSelected channels:"
            for i in self.channels:
                description += "\n> <#" + str(i) + ">"

        if self.roles.size > 0:
            description += "\nSelected roles:"
            for i in self.roles:
                description += "\n> <@&" + str(i) + ">"

        if self.users.size > 0:
            description += "\nSelected users:"
            for i in self.users:
                description += "\n> <@" + str(i) + ">"

        description += "\n"
        return description



async def remove_after_timeout(ctx: tanjun.abc.Context, DB: Session):
    await asyncio.sleep(Config.QUEUE_JOIN_TIMEOUT)
    queue = DB.get_lobbies(channel_id=ctx.channel_id).iloc[
        0]  # would probably break if the channel was deleted after the player joined
    queue["player"] = None
    DB.upsert_lobby(queue)
    await ctx.get_channel().send(
        "The player was removed from the queue after " + str(Config.QUEUE_JOIN_TIMEOUT // 60) + " minutes")


async def remove_from_queue(ctx: tanjun.abc.Context, DB: Session, lobby):
    for i in asyncio.all_tasks():
        if i.get_name() == str(ctx.author.id) + str(lobby.name) + "_queue_timeout":
            i.cancel()
    lobby["player"] = None
    DB.upsert_lobby(lobby)


async def start_new_match(ctx:tanjun.abc.Context, p1_info, p2_info, client):
    """creates a new match between the 2 players and announces it to the channel"""

    DB = Session(ctx.guild_id)

    p1_ping = "<@" + str(p1_info.name) + ">"
    p2_ping = "<@" + str(p2_info.name) + ">"

    p1_is_ranked = p1_info["is_ranked"]
    p2_is_ranked = p2_info["is_ranked"]

    new_match = DB.get_new_match()
    new_match[["time_started", "p1_id", "p2_id", "p1_elo", "p2_elo", "p1_is_ranked", "p2_is_ranked"]] = \
        [datetime.now(), p1_info.name, p2_info.name, p1_info["elo"], p2_info["elo"], p1_is_ranked, p2_is_ranked]

    DB.upsert_match(new_match)

    embed = Custom_Embed(type=Embed_Type.INFO, title="Match " + str(new_match.name) + " started", description=p1_info["tag"] + " vs " + p2_info["tag"])

    await announce_as_match_update(ctx, embed, content=p1_ping+ " " + p2_ping, client=client)

def describe_match(match: pd.Series, DB): # TODO take the match id

    p1_tag = DB.get_players(user_id=match["p1_id"]).iloc[0]["tag"]
    p2_tag = DB.get_players(user_id=match["p2_id"]).iloc[0]["tag"]

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

    color = Colors.SUCCESS
    if match["outcome"] == Outcome.PLAYER_1:
        result = str(DB.get_players(user_id=match["p1_id"]).iloc[0]["username"]) + " won"
    elif match["outcome"] == Outcome.PLAYER_2:
        result = str(DB.get_players(user_id=match["p2_id"]).iloc[0]["username"]) + " won"
    elif match["outcome"] == Outcome.CANCEL:
        result = "Cancelled"
        color = Colors.NEUTRAL
    elif match["outcome"] == Outcome.DRAW:
        result = "Draw"
    else:
        result = "Undecided"
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

    embed.add_field(name=result, value="*_ _*")

    embed.add_field(name=str(p1_tag), value=str(p1_prior_elo_displayed) + " -> " + str(p1_after_elo_displayed) + "\n " + p1_declared, inline=True)
    embed.add_field(name="vs", value="*_ _*", inline=True)
    embed.add_field(name=str(p2_tag), value=str(p2_prior_elo_displayed) + " -> " + str(p2_after_elo_displayed) + "\n " + p2_declared, inline=True)

    embed.set_footer(text=match["time_started"].strftime("%B %d, %Y, %H:%M") + " UTC")

    return embed


async def announce_as_match_update(ctx, embed, client:tanjun.Client, content=None):
    DB = Session(ctx.guild_id)

    config = DB.get_config()
    channel_id = config["results_channel"]

    if channel_id is None:

        embed.set_footer(text="ℹ Announcing here because no match announcements channel is set. Type /config match-updates-channel to set one.")
        await ctx.get_channel().send(embed=embed)
        return
    await client.rest.create_message(channel_id, content=content, embed=embed, user_mentions=True)


async def update_player_elo_roles(ctx:tanjun.abc.Context, bot:hikari.GatewayBot, user_id):

    DB = Session(ctx.guild_id)

    player = DB.get_players(user_id=user_id).iloc[0]
    if not player["is_ranked"]:
        return

    elo = player["elo"]
    elo_roles = DB.get_elo_roles()

    try:
        for role_id, role_info in elo_roles.iterrows(): # could sort by ascending min elo and remove all roles every iteration to ensure everyone only gets 1 role
            if role_info["min_elo"] <= elo <= role_info["max_elo"]:
                await bot.rest.add_role_to_member(ctx.guild_id, user_id, role_id)
            else:
                await bot.rest.remove_role_from_member(ctx.guild_id, user_id, role_id)

    except hikari.ForbiddenError:
        await ctx.respond(embed=Custom_Embed(type=Embed_Type.ERROR, title="Unable to update roles", description="Please make sure the bot's role is above all elo roles"))

__all__ = ["InputParser", "describe_match", "announce_as_match_update", "update_player_elo_roles", "remove_after_timeout", "remove_from_queue", "start_new_match", "update_matches", "determine_is_ranked"]