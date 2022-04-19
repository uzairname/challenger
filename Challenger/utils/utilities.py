import hikari
import tanjun
import re
import numpy as np

import pandas as pd

from .scoring import *
from .style import *
from ..database import Session


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


async def announce_as_match_update(ctx, embed, client=tanjun.injected(type=tanjun.abc.Client)):
    DB = Session(ctx.guild_id)

    config = DB.get_config()
    channel_id = config["results_channel"]

    if channel_id is None:

        embed.set_footer(text="ℹ Announcing here because no match announcements channel is set. Type /config match-updates-channel to set one.")
        await ctx.get_channel().send(embed=embed)
        return
    await client.rest.create_message(channel_id, embed=embed)


async def update_player_elo_roles(ctx:tanjun.abc.Context, bot:hikari.GatewayBot, user_id):

    DB = Session(ctx.guild_id)

    elo = DB.get_players(user_id=user_id).iloc[0]["elo"]
    elo_roles = DB.get_elo_roles()

    try:
        for role_id, role_info in elo_roles.iterrows(): # could sort by ascending min elo and remove all roles every iteration to ensure everyone only gets 1 role
            if role_info["min_elo"] <= elo <= role_info["max_elo"]:
                await bot.rest.add_role_to_member(ctx.guild_id, user_id, role_id)
            else:
                await bot.rest.remove_role_from_member(ctx.guild_id, user_id, role_id)

    except hikari.ForbiddenError:
        await ctx.respond(embed=Custom_Embed(type=Embed_Type.ERROR, title="Unable to update roles", description="Please make sure the bot's role is above all elo roles"))

__all__ = ["InputParser", "describe_match", "announce_as_match_update", "update_player_elo_roles"]