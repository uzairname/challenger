import pandas as pd


from .elo_calculation import *



def recalculate_matches(matches, match_id, new_outcome=None, updated_players=None, update_all=False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    starts from match_id and recalculates all matches after it.
    if new_starting_elo is set, it will update everyone's elo before any matches were played

    params:
        matches: a DataFrame of matches. must have index "match_id", and columns "p1_id", "p2_id", "p1_elo", "p2_elo", "p1_elo_after", "p2_elo_after", "p1_is_ranked", "p2_is_ranked", "p1_is_ranked_after", "p2_is_ranked_after", "outcome"
        match_id: the match id of the first match to be updated
        new_outcome: the new outcome of the match
        updated_players: pd.DataFrame of updated players. must have index user_id, columns "elo", "is_ranked"

    returns:
        updated_matches a DataFrame of the matches with updated prior and after elos and ranked status for each match affected by the outcome change.
        updated_players a DataFrame of each player's new elo and ranked status
    """

    matches = matches.copy()
    updated_players = updated_players.copy() if updated_players is not None else None

    if updated_players is None:
        updated_players = pd.DataFrame([], columns=["user_id", "elo", "is_ranked"]).set_index("user_id")

    match = matches.loc[match_id]

    p1_id = match["p1_id"]
    p2_id = match["p2_id"]

    #If this match should be affected in any way, calculate the players' new elos. If not, move on to the next match
    if p1_id in updated_players.index or p2_id in updated_players.index or new_outcome is not None or update_all:

        #By default their prior elo is what it is in the database. If it changed, update it

        p1_elo = matches.loc[match_id, "p1_elo"]
        p2_elo = matches.loc[match_id, "p2_elo"]

        for user_id, player in updated_players.iterrows():
            if user_id == p1_id:
                p1_elo = updated_players.loc[user_id, "elo"]
                matches.loc[match_id, "p1_elo"] = p1_elo

            if user_id == p2_id:
                p2_elo = updated_players.loc[user_id, "elo"]
                matches.loc[match_id, "p2_elo"] = p2_elo

        #New outcome
        outcome = match["outcome"]
        if new_outcome is not None:
            outcome = new_outcome
            matches.loc[match_id, "outcome"] = new_outcome

        #determine whether they're ranked based on the new outcome
        matches.loc[match_id, "p1_is_ranked"] = determine_is_ranked(matches, player_id=p1_id, latest_match_id=match_id-1)
        matches.loc[match_id, "p2_is_ranked"] = determine_is_ranked(matches, player_id=p2_id, latest_match_id=match_id-1)
        matches.loc[match_id, "p1_is_ranked_after"] = determine_is_ranked(matches, player_id=p1_id, latest_match_id=match_id)
        matches.loc[match_id, "p2_is_ranked_after"] = determine_is_ranked(matches, player_id=p2_id, latest_match_id=match_id)


        if matches.loc[match_id, "p1_is_ranked"]:
            p1_elo_after = p1_elo + calc_elo_change(p1_elo, p2_elo, outcome)[0]
        else:
            p1_elo_after = p1_elo + calc_provisional_elo_change(p1_elo, p2_elo, outcome)[0]

        if matches.loc[match_id, "p2_is_ranked"]:
            p2_elo_after = p2_elo + calc_elo_change(p1_elo, p2_elo, outcome)[1]
        else:
            p2_elo_after = p2_elo + calc_provisional_elo_change(p1_elo, p2_elo, outcome)[1]

        matches.loc[match_id, "p1_elo_after"] = p1_elo_after
        matches.loc[match_id, "p2_elo_after"] = p2_elo_after


        updated_players.loc[p1_id, "elo"] = p1_elo_after
        updated_players.loc[p2_id, "elo"] = p2_elo_after
        updated_players.loc[p1_id, "is_ranked"] = matches.loc[match_id, "p1_is_ranked_after"]
        updated_players.loc[p2_id, "is_ranked"] = matches.loc[match_id, "p2_is_ranked_after"]

    if match_id + 1 in matches.index:
        return recalculate_matches(matches=matches, match_id=match_id + 1, updated_players=updated_players, update_all=update_all)
    else:
        return matches, updated_players




def determine_is_ranked(all_matches, player_id, latest_match_id):
    return True

    # """
    #     Counts all the matches the player has played in before the current match that weren't cancelled or undecided
    #     if they have played enough matches, they are ranked
    # """
    # player_matches = all_matches.loc[np.logical_or(all_matches["p1_id"] == player_id, all_matches["p2_id"] == player_id)]
    # finished_matches = player_matches.loc[player_matches.index <= latest_match_id].loc[player_matches["outcome"].isin(Outcome.PLAYED)]
    #
    # return len(finished_matches) >= Elo.NUM_PLACEMENT_MATCHES