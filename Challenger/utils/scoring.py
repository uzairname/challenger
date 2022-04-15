from Challenger.utils.utils import *
from Challenger.config import Config
import math
import sympy as sp
import numpy as np


class Outcome:
    PLAYER_1 = "player 1"
    PLAYER_2 = "player 2"
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    CANCEL = "cancelled"
    UNDECIDED = "undecided"

class Declare:
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    CANCEL = "cancel"


ELO_STDEV = 150  # estimate of standard deviation of everyone's elo
DEFAULT_ELO = 1000  # everyone's starting score
DEFAULT_SCALE = ELO_STDEV * 2.7  # Used in elo calculation. 2.7 is an arbitrary scaling factor
DEFAULT_K = 30  # maximum change in one game
NUM_UNRANKED_MATCHES = 2  # number of matches to play before ranking



def calc_elo_change(p1_elo, p2_elo, result:Outcome) -> typing.List[float]:
    if result == Outcome.CANCEL or result is None:
        return [0,0]
    allocated = {Outcome.PLAYER_1:1, Outcome.PLAYER_2:0, Outcome.DRAW:0.5}[result] #what percent of the elo gets allocated to player 1

    k = DEFAULT_K
    scale = DEFAULT_SCALE

    def p(A, B): #probability of A beating B
        return 1 / (1 + math.pow(10, -(A - B) / scale))

    p1_elo_change = (  allocated   - p(p1_elo, p2_elo)) * k
    p2_elo_change = ((1-allocated) - p(p2_elo, p1_elo)) * k

    return [p1_elo_change, p2_elo_change]



def calc_bayeselo(game_results, avg_elo=DEFAULT_ELO, std_elo=150, initial_std=1):
    #game_results is a list of tuples of the form (opponent_elo, result(win/lose))
    raise NotImplementedError


def calc_prov_elo(p1_elo, p2_elo, result):
    return np.array(calc_elo_change(p1_elo, p2_elo, result))*3





