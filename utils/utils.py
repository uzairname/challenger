import functools
import logging
import tanjun
import math
import numpy as np
import pandas as pd
import re
import sympy as sp


PELA_CYAN = "5effcc"

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


def parse_input(string):
    text_pat = r"[a-zA-Z\d\s]+"

    channel_pat = r"<#(\d{17,19})>"
    role_pat = r"<@&(\d{17,19})>"
    user_pat = r"<@!?(\d{17,19})>"
#(
    name = re.match(text_pat, string)
    if name:
        name = name[0].strip()

    channels = np.array(re.findall(channel_pat, string)).astype("int64")
    roles = np.array(re.findall(role_pat, string)).astype("int64")
    users = np.array(re.findall(user_pat, string)).astype("int64")

    #text is all text at the start before any channel roles or users
    return {"text": name, "channels": channels, "roles": roles, "users":users}


