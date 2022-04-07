from utils.utils import *


ELO_STDEV = 150 # estimate of standard deviation of everyone's elo
DEFAULT_ELO = 1000  # everyone's starting score
DEFAULT_SCALE = ELO_STDEV*2.7  # Used in elo calculation. 2.7 is just an arbitrary scaling factor
DEFAULT_K = 30  # maximum change in one game

NUM_UNRANKED_MATCHES = 2  # number of matches to play before ranking


def calc_elo_change(p1_elo, p2_elo, result): #
    if result == results.CANCEL or result is None:
        return [0,0]
    allocated = {results.PLAYER_1:1, results.PLAYER_2:0, results.DRAW:0.5}[result] #what percent of the elo gets allocated to player 1

    k = DEFAULT_K
    scale = DEFAULT_SCALE

    def p(A, B):  #probability of A beating B
        return 1 / (1 + math.pow(10, -(A - B) / scale))

    p1_elo_change = (  allocated   - p(p1_elo, p2_elo)) * k
    p2_elo_change = ((1-allocated) - p(p2_elo, p1_elo)) * k

    return [p1_elo_change, p2_elo_change]



def calc_bayeselo(game_results, avg_elo=DEFAULT_ELO, std_elo=150, initial_std=1):

    return None


def calc_prov_elo(p1_elo, p2_elo, result):
    return np.array(calc_elo_change(p1_elo, p2_elo, result))*3





