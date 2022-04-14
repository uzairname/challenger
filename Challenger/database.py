import typing

import pymongo
from Challenger.config import Config
import os
import pandas as pd
import numpy as np


class Database:

    empty_player = pd.DataFrame([], columns=["user_id", "tag", "username", "time_registered", "elo", "is_ranked", "staff"]).set_index("user_id")
    empty_match = pd.DataFrame([], columns=["match_id", "time_started", "outcome", "staff_declared",
                                            "p1_id", "p1_elo", "p1_elo_after", "p1_declared", "p1_is_ranked", "p1_is_ranked_after",
                                            "p2_id", "p2_elo", "p2_elo_after", "p2_declared", "p2_is_ranked", "p2_is_ranked_after"]).set_index("match_id")
    #p1 and p2 elo: elo before the match. p1 and p1 is_ranked: whether the player's elo was ranked before the match was decided
    empty_lobby = pd.DataFrame([], columns=["channel_id", "lobby_name", "role_required", "player", "time_joined"])
    empty_elo_roles = pd.DataFrame([], columns=["role", "elo_min", "elo_max", "priority"])

    empty_config = pd.Series(index=["results_channel", "staff_role", "guild_name"], dtype="float64").replace(np.nan, None)
    empty_config_df = pd.DataFrame([], columns=["guild_name", "default_results_channel", "staff_role"])

    players_tbl = "players"
    matches_tbl = "matches"
    queues_tbl = "queues"
    config_tbl = "config"
    elo_roles_tbl = "elo_roles"
    required_tables = [players_tbl, matches_tbl, queues_tbl, config_tbl, elo_roles_tbl]

    def __init__(self, guild_id):
        self.guild_id = guild_id
        url = os.environ.get("MONGODB_URL")
        client = pymongo.MongoClient(url)

        self.guild_name = str(guild_id)

        if guild_id == Config.PX_GUILD_ID:
            self.guild_name = "PX"
        elif guild_id == Config.TESTING_GUILD_ID:
            self.guild_name = "testing"

        self.guildDB = client["guild_" + self.guild_name]


    def setup_test(self): #always called at the start

        player_id = np.array([623257053879861248])[0]
        num_matches=3
        m = self.get_matches(match_id=3)
        print(m)

        pass

    def init_database(self):
        existing_tables = self.guildDB.list_collection_names()
        for i in self.required_tables:
            if i in existing_tables:
                continue
            self.guildDB.create_collection(i)


    #get always returns a properly formatted series or DF, even if there doesn't exist one. can pass a series from these to upsert __. An empty series works

    def get_players(self, user_id=None, user_ids:typing.List=None, staff=None, top_by_elo=None) -> pd.DataFrame:

        #dataframe of all players
        cur_filter = {}
        if user_ids is not None:
            cur_filter["user_id"] = {"$in": user_ids}
        if user_id:
            cur_filter["user_id"] = int(user_id)
        if staff:
            cur_filter["staff"] = staff

        cur = self.guildDB[self.players_tbl].find(cur_filter, projection={"_id":False})

        if top_by_elo:
            cur.sort("elo", -1)
            cur.skip(top_by_elo[0])
            cur.limit(top_by_elo[1])

        players_df = pd.DataFrame(list(cur))
        if not players_df.empty:
            players_df.set_index("user_id", inplace=True)
        full_players_df = pd.concat([self.empty_player, players_df])[self.empty_player.columns].replace(np.nan, None)
        return full_players_df

    def get_new_player(self, user_id) -> pd.Series:
        player_df = pd.DataFrame([[user_id]], columns=["user_id"]).set_index("user_id")
        new_player = pd.concat([self.empty_player, player_df]).iloc[0]
        return new_player

    def upsert_player(self, player:pd.Series): #takes a series returned from get_players or new_player

        player = player.replace(np.nan, None)

        player["user_id"] = int(player.name)
        if player["staff"] is not None:
            player["staff"] = int(player["staff"])
        if player["elo"] is not None:
            player["elo"] = float(player["elo"])

        playerdict = player.to_dict()
        self.guildDB[self.players_tbl].update_one({"user_id":playerdict["user_id"]}, {"$set":playerdict}, upsert=True)

    def upsert_players(self, players:pd.DataFrame):
        for i, row in players.iterrows():
            self.upsert_player(row)


    def get_matches(self, user_id=None, match_id=None, from_match=None, up_to_match=None, number=None, from_first=False) -> pd.DataFrame:

        cur_filter = {}
        if user_id:
            user_id = int(user_id)
            cur_filter["$or"] = [{"p1_id":user_id}, {"p2_id":user_id}]

        if match_id:
            match_id = int(match_id)
            cur_filter["match_id"] = match_id

        if from_match:
            from_match = int(from_match)
            cur_filter["match_id"] = {"$gte":from_match}

        if up_to_match:
            up_to_match = int(up_to_match)
            cur_filter["match_id"] = {"$lte":up_to_match}

        sort_order = 1 if from_first else -1
        cur = self.guildDB[self.matches_tbl].find(cur_filter, projection={"_id":False}).sort("match_id", sort_order)
        if number:
            cur.limit(number)

        matches_df = pd.DataFrame(list(cur), dtype="object")
        if not matches_df.empty:
            matches_df.set_index("match_id", inplace=True)
        full_matches_df = pd.concat([self.empty_match, matches_df])[self.empty_match.columns].replace(np.nan, None)
        return full_matches_df

    def get_new_match(self) -> pd.Series:

        prev_match = self.get_matches(number=1)
        if prev_match.empty:
            new_id = 0
        else:
            new_id = prev_match.iloc[0].name + 1

        match_df = pd.DataFrame([[new_id]], columns=["match_id"]).set_index("match_id")
        new_match = pd.concat([self.empty_match, match_df]).iloc[0]
        return new_match


    def upsert_match(self, match:pd.Series):
        match["match_id"] = match.name #match_id is the index of the match
        match = match.replace(np.nan, None) #replace nan with none fixes the types. set dtype to object

        match["match_id"] = int(match["match_id"])
        if match["p1_id"] is not None:
            match["p1_id"] = int(match["p1_id"])
        if match["p2_id"] is not None:
            match["p2_id"] = int(match["p2_id"])

        matchdict = match.to_dict()
        self.guildDB[self.matches_tbl].update_one({"match_id":matchdict["match_id"]}, {"$set":matchdict}, upsert=True)

    def upsert_matches(self, matches:pd.DataFrame):
        for i in matches.index:
            self.upsert_match(matches.loc[i])


    def get_queues(self, channel_id = None) -> pd.DataFrame:
        cur_filter = {}
        if channel_id:
            cur_filter["channel_id"] = int(channel_id)

        cur = self.guildDB[self.queues_tbl].find(cur_filter, projection={"_id":False})

        queues_df =  pd.DataFrame(list(cur))
        updated_queues_df = pd.concat([self.empty_lobby, queues_df])[self.empty_lobby.columns].replace(np.nan, None)
        return updated_queues_df.reset_index(drop=True)

    def get_new_queue(self, channel_id) -> pd.Series:
        queue = pd.Series([channel_id], index=["channel_id"])
        new_queue = pd.concat([self.empty_lobby, pd.DataFrame(queue).T]).iloc[0]
        return new_queue

    def upsert_queue(self, queue:pd.Series): # only pass something returned from new_queue or get_queue
        queue = queue.replace(np.nan, None)

        self.empty_lobby #Make sure nothning is numpy type
        if queue["channel_id"] is not None:
            queue["channel_id"] = int(queue["channel_id"])
        if queue["player"] is not None:
            queue["player"] = int(queue["player"])
        if queue["role_required"] is not None:
            queue["role_required"] = int(queue["role_required"])

        queuedict = queue.to_dict()
        self.guildDB[self.queues_tbl].update_one({"channel_id":queuedict["channel_id"]}, {"$set":queuedict}, upsert=True)

    def remove_queue(self, channel_id):
        self.guildDB[self.queues_tbl].delete_one({"channel_id":channel_id})


    def get_config(self) -> pd.Series:
        cur = self.guildDB[self.config_tbl].find({}, projection={"_id":False})

        if cur is None:
            self.upsert_config(self.empty_config)
            return self.get_config()

        return pd.Series(cur[0], dtype="object").replace(np.nan, None)

    def upsert_config(self, config:pd.Series): # takes a series returned from get_config
        configdict = config.to_dict()
        self.guildDB[self.config_tbl].update_one({}, {"$set":configdict}, upsert=True)

    def upsert_elo_roles(self, elo_roles_df:pd.DataFrame):
        self.guildDB[self.elo_roles_tbl].update_many({}, {"$set":elo_roles_df.to_dict("tight")}, upsert=True)

    def get_elo_roles(self) -> pd.DataFrame:
        cur = self.guildDB[self.elo_roles_tbl].find_one()

        if cur is None:
            df = pd.DataFrame.to_dict(self.empty_elo_roles, orient="tight")
            df = pd.DataFrame.from_dict(df, orient="tight")
            self.upsert_elo_roles(self.empty_elo_roles)
            return df

        elo_roles_df = pd.DataFrame.from_dict(cur, orient="tight")
        elo_roles_df = pd.concat([self.empty_elo_roles, elo_roles_df]).replace(np.nan, None)
        return elo_roles_df.reset_index(drop=True)


    def update_guild_name(self, guild_name:str):
        config = self.get_config()
        config["guild_name"] = guild_name
        self.upsert_config(config)