import pandas as pd


from .elo_calculation import *



def recalculate_matches(matches_df, match_id, new_outcome=None, updated_players_df=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    starts from match_id and recalculates all matches after it.

    params:
        matches: a DataFrame of matches. must have index "match_id", and columns
            "player_1_id", "player_2_id",
            "player_1_elo", "player_2_elo",
            "player_1_RD", "player_2_RD",
            "outcome"
        match_id: the match id of the first match to be updated
        new_outcome: the new outcome of the match
        updated_players: pd.DataFrame of updated players. must have index user_id, columns "elo", "is_ranked"

    returns:
        updated_matches: a DataFrame of the matches with updated prior elos and SD for each match affected by the outcome change.
        updated_players: a DataFrame of each player's new elo and ranked status
    """


    matches_df = matches_df.copy()
    updated_players_df = updated_players_df.copy() if updated_players_df is not None else None

    if updated_players_df is None:
        updated_players_df = pd.DataFrame([], columns=["user_id", "elo", "is_ranked"]).set_index("user_id")


    # for index, row in matches_df.iterrows():
    match = matches_df.loc[match_id]

    p1_id = match["player_1"]
    p2_id = match["player_2"]

    #If this match should be affected in any way, calculate the players' new elos. If not, move on to the next match
    if p1_id in updated_players_df.index or p2_id in updated_players_df.index or new_outcome is not None:

        #Determine their prior elo
        p1_elo = matches_df.loc[match_id, "player_1_elo"]
        p2_elo = matches_df.loc[match_id, "player_2_elo"]

        for user_id, player in updated_players_df.iterrows():
            if user_id == p1_id:
                p1_elo = updated_players_df.loc[user_id, "elo"]
                matches_df.loc[match_id, "player_1_elo"] = p1_elo

            if user_id == p2_id:
                p2_elo = updated_players_df.loc[user_id, "elo"]
                matches_df.loc[match_id, "player_2_elo"] = p2_elo

        #Determine the new outcome
        outcome = match["outcome"]
        if new_outcome is not None:
            outcome = new_outcome
            matches_df.loc[match_id, "outcome"] = new_outcome

        #determine whether they're ranked based on the new outcome
        p1_is_ranked = determine_is_ranked(matches_df, player_id=p1_id, latest_match_id=match_id - 1)
        p2_is_ranked = determine_is_ranked(matches_df, player_id=p2_id, latest_match_id=match_id - 1)


        # Calculate the new elo and RD for each player
        if p1_is_ranked:
            p1_elo_after = p1_elo + calc_elo_change(p1_elo, p2_elo, outcome)[0]
        else:
            p1_elo_after = p1_elo + calc_provisional_elo_change(p1_elo, p2_elo, outcome)[0]

        if p2_is_ranked:
            p2_elo_after = p2_elo + calc_elo_change(p1_elo, p2_elo, outcome)[1]
        else:
            p2_elo_after = p2_elo + calc_provisional_elo_change(p1_elo, p2_elo, outcome)[1]

        # Store the new elos
        updated_players_df.loc[p1_id, "elo"] = p1_elo_after
        updated_players_df.loc[p2_id, "elo"] = p2_elo_after
        updated_players_df.loc[p1_id, "is_ranked"] = p1_is_ranked
        updated_players_df.loc[p2_id, "is_ranked"] = p2_is_ranked

    #repeat for following matches
    if match_id + 1 in matches_df.index:
        return recalculate_matches(matches_df=matches_df, match_id=match_id + 1, updated_players_df=updated_players_df)
    else:
        return matches_df, updated_players_df




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