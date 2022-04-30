from enum import Enum


BLANK = "*_ _*"


class Outcome(str, Enum):
    PLAYER_1 = "player 1"
    PLAYER_2 = "player 2"
    DRAW = "draw"
    CANCELLED = "cancelled"
    PENDING = "undecided"


PLAYED = [Outcome.PLAYER_1, Outcome.PLAYER_2, Outcome.DRAW]


class Declare(str, Enum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    CANCEL = "cancel"
    UNDECIDED = "didn't declare"


class Colors:
    PRIMARY = "#fccb6f"
    SECONDARY = "#00baab"
    DARK = "#656565"
    SUCCESS = "#49c47b"
    WARNING = "#e6d220"
    ERROR = "#db4737"


__all__ = ["BLANK", "Outcome", "Declare", "Colors"]