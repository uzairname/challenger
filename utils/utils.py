import functools
import logging
import hikari
import tanjun
import math
import numpy as np
import pandas as pd
import re
import sympy as sp


class Colors:
    PRIMARY = "37dedb"
    CONFIRM = "ffe373"
    SUCCESS = "#5dde07"

DEFAULT_TIMEOUT = 120

class results:
    PLAYER_1 = "player 1"
    PLAYER_2 = "player 2"
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    CANCEL = "cancelled"
    UNDECIDED = "undecided"

class declares:
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    CANCEL = "cancel"

class status:
    NONE = 0
    STAFF = 1

def check_errors(func):
    # for commands that take a context, respond with an error if it doesn't work
    @functools.wraps(func)
    async def wrapper_check_errors(ctx: tanjun.abc.Context, *args, **kwargs):
        try:
            await func(ctx, *args, **kwargs)
        except BaseException:
            await ctx.respond("didnt work :(", ensure_result=True)
            logging.info("command failed: " + str(kwargs.values()))
    return wrapper_check_errors


def construct_df(rows, columns, index_column: str = None):
    df = pd.DataFrame(rows, columns=columns)
    if index_column:
        df.set_index(df[index_column], inplace=True)
    return df


def replace_row_if_col_matches(df:pd.DataFrame, row:pd.Series, column:str):

    drop_index = df.loc[df[column] == row[column]].index
    new_df = pd.concat([df.drop(drop_index), pd.DataFrame(row).T])

    return new_df

def sqlarray_to_list(string):
    text_pat = r"[\d]+"
    return re.findall(text_pat, string)





class InputParams():
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
            description += "Input: **" + str(self.text) + "**\n"

        if self.channels.size > 0:
            description += "Selected channels:\n"
            for i in self.channels:
                description += "<#" + str(i) + ">\n"

        if self.roles.size > 0:
            description += "Selected roles:\n"
            for i in self.roles:
                description += "<@&" + str(i) + ">\n"

        if self.users.size > 0:
            description += "Selected users:\n"
            for i in self.users:
                description += "<@" + str(i) + ">\n"

        return description


async def is_staff(ctx:tanjun.abc.Context, DB):
    staff_role = DB.get_config()["staff_role"]

    if staff_role is None:
        guild = await ctx.fetch_guild()

        roles = ctx.member.role_ids
        role_mapping = {}
        for role in roles:
            role_mapping[role] = guild.get_role(role)

        perms = tanjun.utilities.calculate_permissions(member=ctx.member, guild=guild, roles=role_mapping)
        if perms & hikari.Permissions.MANAGE_GUILD:
            return True
        return False

    return bool(staff_role in ctx.member.role_ids)