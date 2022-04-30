from .constants import *

def convert_to_ordinal(number):
    """
    Converts a number to its ordinal form.
    """
    if number % 100 // 10 == 1:
        return '%dth' % number
    elif number % 10 == 1:
        return '%dst' % number
    elif number % 10 == 2:
        return '%dnd' % number
    elif number % 10 == 3:
        return '%drd' % number
    else:
        return '%dth' % number


def desired_outcome(player_declared:Declare, player:int) -> Outcome:
    """
    Returns the outcome of the game that the given player has declared
    """

    return {
        Declare.WIN: Outcome.PLAYER_1 if player==1 else Outcome.PLAYER_2,
        Declare.LOSS: Outcome.PLAYER_2 if player==1 else Outcome.PLAYER_1,
        Declare.DRAW: Outcome.DRAW,
        Declare.CANCEL: Outcome.CANCELLED
    }[player_declared]