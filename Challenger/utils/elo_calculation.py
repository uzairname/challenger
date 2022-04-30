from typing import List
import math
import numpy as np

from .constants import *
from ..config import Elo

def calc_elo_change(p1_elo, p2_elo, outcome:Outcome) -> List[float]:
    if outcome == Outcome.CANCELLED or outcome is None:
        return [0,0]

    def p(A, B): #probability of A beating B
        return 1 / (1 + math.pow(10, -(A - B) / Elo.SCALE))

    elo_outcome = {Outcome.PLAYER_1:1, Outcome.PLAYER_2:0, Outcome.DRAW:0.5}[outcome] #what percent of the elo gets allocated to player 1
    p1_elo_change = Elo.K*(  elo_outcome   - p(p1_elo, p2_elo))
    p2_elo_change = Elo.K*((1-elo_outcome) - p(p2_elo, p1_elo))

    return [p1_elo_change, p2_elo_change]


def calc_provisional_elo_change(p1_elo, p2_elo, result):
    return np.array(calc_elo_change(p1_elo, p2_elo, result))*1.5