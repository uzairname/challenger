import functools
import logging
import tanjun
import math
import numpy as np
import pandas as pd
import re


class results:
    PLAYER_1 = "player 1"
    PLAYER_2 = "player 2"
    DRAW = "draw"
    CANCEL = "cancel"

class declares:
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    CANCEL = "cancel"

class status:
    STAFF = 1


DEFAULT_ELO = 50  # everyone's starting score
DEFAULT_K = 12  # maximum change in one game
DEFAULT_SCALE = 30  # elo difference approximating 10x skill difference

def calc_elo_change(p1_elo, p2_elo, result): #
    if result == results.CANCEL or result is None:
        return [0,0]

    k = DEFAULT_K
    scale = DEFAULT_SCALE

    def p(A, B):  #probability of A beating B
        return 1 / (1 + math.pow(10, -(A - B) / scale))

    allocated = {results.PLAYER_1:1, results.PLAYER_2:0, results.DRAW:0.5}[result] #what percent of the elo gets allocated to player 1
    p1_elo_change = (  allocated   - p(p1_elo, p2_elo)) * k
    p2_elo_change = ((1-allocated) - p(p2_elo, p1_elo)) * k

    return [p1_elo_change, p2_elo_change]


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