from typing import List

from Challenger.utils import *
from Challenger.config import *

import math
import numpy as np
import sympy as sp


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


def calc_elo_change(p1_elo, p2_elo, result:Outcome) -> List[float]:
    if result == Outcome.CANCEL or result is None:
        return [0,0]
    allocated = {Outcome.PLAYER_1:1, Outcome.PLAYER_2:0, Outcome.DRAW:0.5}[result] #what percent of the elo gets allocated to player 1

    k = Elo.K
    scale = Elo.SCALE

    def p(A, B): #probability of A beating B
        return 1 / (1 + math.pow(10, -(A - B) / scale))

    p1_elo_change = (  allocated   - p(p1_elo, p2_elo)) * k
    p2_elo_change = ((1-allocated) - p(p2_elo, p1_elo)) * k

    return [p1_elo_change, p2_elo_change]



def calc_bayeselo(game_results):
    """
     game_results is a list of tuples of the form (opponent_elo, result(win/lose))
    """

    est_STD = Elo.K


def calc_prov_elo(p1_elo, p2_elo, result):
    return np.array(calc_elo_change(p1_elo, p2_elo, result))*3



__all__ = ["calc_elo_change", "calc_bayeselo", "calc_prov_elo", "Outcome", "Declare"]