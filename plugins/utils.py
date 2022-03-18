import functools
import logging
import tanjun
import math
import numpy as np
import pandas as pd
import re

class results:
    PLAYER1 = "player 1"
    PLAYER2 = "player 2"
    DRAW = "draw"
    CANCEL = "cancelled"


DEFAULT_ELO = 50  # everyone's starting score
DEFAULT_K = 12  # maximum change in one game
DEFAULT_SCALE = 30  # elo difference approximating 10x skill difference

def calc_elo_change(p1_elo, p2_elo, result): #player 1's elo change

    k = DEFAULT_K
    scale = DEFAULT_SCALE
    def p(A, B):  # A's expected probability of winning
        return 1 / (1 + math.pow(10, -(B - A) / scale))

    if result == results.PLAYER1:
        p1_elo_change = k * p(p1_elo, p2_elo)
        p2_elo_change =  k * (p(p2_elo, p1_elo)-1)
    elif result == results.PLAYER2:
        p1_elo_change =  k * (p(p1_elo, p2_elo)-1)
        p2_elo_change = k * p(p2_elo, p1_elo)
    elif result == results.DRAW:
        p1_elo_change =  k * (p(p1_elo, p2_elo)-0.5)
        p2_elo_change = k * (p(p2_elo, p1_elo)-0.5)
    elif result == results.CANCEL or result is None:
        p1_elo_change = 0
        p2_elo_change = 0
    else:
        raise

    return np.array([p1_elo_change, p2_elo_change])


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