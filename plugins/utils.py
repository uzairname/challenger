import functools
import logging
import tanjun
import asyncio
import math
from __main__ import DB
import numpy as np


class results:
    WIN = "won"
    LOSE = "lost"
    PLAYER1 = "player 1"
    PLAYER2 = "player 2"
    CANCEL = "cancelled"




DEFAULT_ELO = 50 #everyone's starting score
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
