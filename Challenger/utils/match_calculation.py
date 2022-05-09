import pandas as pd


from .elo_calculation import *


def recalculate_matches(matches, match_id, new_outcome=None, updated_players=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    starts from match_id and recalculates all matches after it.

    params:
        matches: a DataFrame of matches. must have index "match_id", and columns
            "player_1_id", "player_1_elo", "player_1_RD",
            "player_2_id", "player_2_elo", "player_2_RD",
            "outcome"
        match_id: the match id of the first match to be updated
        new_outcome: the new outcome of the match
        updated_players: pd.DataFrame of updated players. must have index user_id, columns "elo", "RD"

    returns:
        updated_matches: a DataFrame of the matches with updated prior elos and SD for each match affected by the outcome change.
        updated_players: a DataFrame of each player's new elo and ranked status
    """

    matches = matches.copy()
    updated_players = updated_players.copy() if updated_players is not None else None

    if updated_players is None:
        updated_players = pd.DataFrame([], columns=["user_id", "elo", "RD"]).set_index("user_id")

    # for index, row in matches_df.iterrows():
    match = matches.loc[match_id]

    p1_id = match["player_1"]
    p2_id = match["player_2"]

    #If this match should be affected in any way, calculate the players' new elos. If not, move on to the next match
    if p1_id in updated_players.index or p2_id in updated_players.index or new_outcome is not None:

        #Determine their prior elo
        p1_elo = matches.loc[match_id, "player_1_elo"]
        p2_elo = matches.loc[match_id, "player_2_elo"]

        for player_id, player in updated_players.iterrows():
            if player_id == p1_id:
                p1_elo = updated_players.loc[player_id, "elo"]
                matches.loc[match_id, "player_1_elo"] = p1_elo

            if player_id == p2_id:
                p2_elo = updated_players.loc[player_id, "elo"]
                matches.loc[match_id, "player_2_elo"] = p2_elo

        #Determine the new outcome
        outcome = match["outcome"]
        if new_outcome is not None:
            outcome = new_outcome
            matches.loc[match_id, "outcome"] = new_outcome

        #determine whether they're ranked based on the new outcome
        p1_is_ranked = determine_is_ranked()
        p2_is_ranked = determine_is_ranked()
        elo_change = calc_elo_change(p1_elo, p2_elo, outcome, p1_is_ranked, p2_is_ranked)
        # Calculate the new elo and RD for each player
        p1_elo_after = p1_elo + elo_change[0]
        p2_elo_after = p2_elo + elo_change[1]

        # Store the new elos
        updated_players.loc[p1_id, "elo"] = p1_elo_after
        updated_players.loc[p2_id, "elo"] = p2_elo_after
        updated_players.loc[p1_id, "RD"] = 350
        updated_players.loc[p2_id, "RD"] = 350

    #repeat for following matches
    if match_id + 1 in matches.index:
        return recalculate_matches(matches=matches, match_id=match_id + 1, updated_players=updated_players)
    else:
        return matches, updated_players



def determine_is_ranked():
    return True