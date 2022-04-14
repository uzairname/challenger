from Challenger.utils.utils import *
from Challenger.config import Config
import math
import sympy as sp
import numpy as np


def calc_elo_change(p1_elo, p2_elo, result:Result) -> typing.List[float]:
    if result == Result.CANCEL or result is None:
        return [0,0]
    allocated = {Result.PLAYER_1:1, Result.PLAYER_2:0, Result.DRAW:0.5}[result] #what percent of the elo gets allocated to player 1

    k = Config.DEFAULT_K
    scale = Config.DEFAULT_SCALE

    def p(A, B): #probability of A beating B
        return 1 / (1 + math.pow(10, -(A - B) / scale))

    p1_elo_change = (  allocated   - p(p1_elo, p2_elo)) * k
    p2_elo_change = ((1-allocated) - p(p2_elo, p1_elo)) * k

    return [p1_elo_change, p2_elo_change]



def calc_bayeselo(game_results, avg_elo=Config.DEFAULT_ELO, std_elo=150, initial_std=1):
    #game_results is a list of tuples of the form (opponent_elo, result(win/lose))
    raise NotImplementedError


def calc_prov_elo(p1_elo, p2_elo, result):
    return np.array(calc_elo_change(p1_elo, p2_elo, result))*3





