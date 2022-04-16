import re
import numpy as np

import pandas as pd

from .scoring import *
from .style import *


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



def describe_match(match: pd.Series, DB):

    p1_name = DB.get_players(user_id=match["p1_id"]).iloc[0]["tag"]
    p2_name = DB.get_players(user_id=match["p2_id"]).iloc[0]["tag"]

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


    if match["outcome"] == Outcome.PLAYER_1:
        result = str(DB.get_players(user_id=match["p1_id"]).iloc[0]["username"]) + " won"
    elif match["outcome"] == Outcome.PLAYER_2:
        result = str(DB.get_players(user_id=match["p2_id"]).iloc[0]["username"]) + " won"
    elif match["outcome"] == Outcome.CANCEL:
        result = "Cancelled"
    elif match["outcome"] == Outcome.DRAW:
        result = "Draw"
    else:
        result = "Undecided"


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

    embed = Custom_Embed(type=Embed_Type.INFO, title="Match " + str(match.name))

    embed.add_field(name=result, value="*_ _*")

    embed.add_field(name=str(p1_name), value=str(p1_prior_elo_displayed) + " -> " + str(p1_after_elo_displayed) + "\n " + p1_declared, inline=True)
    embed.add_field(name="vs", value="*_ _*", inline=True)
    embed.add_field(name=str(p2_name), value=str(p2_prior_elo_displayed) + " -> " + str(p2_after_elo_displayed) + "\n " + p2_declared, inline=True)

    embed.set_footer(text=match["time_started"].strftime("%B %d, %Y, %H:%M") + " UTC")

    return embed




__all__ = ["InputParser", "describe_match"]