from plugins.utils import *
from __main__ import DB
import asyncio
import math
from datetime import datetime
import time





component = tanjun.Component(name="player module")




@component.with_slash_command
@tanjun.with_str_slash_option("username", "optional, set a custom username")
@tanjun.as_slash_command("register", "Join the fun!", default_to_ephemeral=True)
async def register(ctx: tanjun.abc.Context, username=None) -> None:
    DB.open_connection()

    #check whether player is registered
    user_id = ctx.author.id

    player_info = DB.get_players(user_id=user_id)
    if not player_info.empty:
        DB.update_player(user_id, username=ctx.author.username)
        await ctx.respond("You have already registered. Updated username")

    DB.add_player(user_id)
    DB.update_player(user_id, username=ctx.author.username, elo=DEFAULT_ELO, time_registered=datetime.fromtimestamp(time.time()))




DEFAULT_ELO = 50 #everyone's starting score
DEFAULT_K = 12  # maximum change in one game
DEFAULT_SCALE = 30  # elo difference approximating 10x skill difference

def calc_elo_change(winner_elo, loser_elo): #winner's elo change. It's negative equals loser's elo change
    diff = winner_elo - loser_elo
    k = DEFAULT_K
    scale = DEFAULT_SCALE
    def expected_score(A, B):  # A's expected probability of winning
        return 1 / (1 + math.pow(10, -(A - B) / scale))
    elo = k * expected_score(loser_elo, winner_elo)  # elo the winner gains
    return elo


def update_player_elo(player1, player2, new_result, old_result):
    pass
    #old result is usually 0.
    #calculate elo for old result, then subtract it.
    #calculate elo for new result, then add it.

    #player 1 lost and has -1.   they should win (loss should've given -3, win should've given +5). new elo is -1--3+5 = 7.

@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())