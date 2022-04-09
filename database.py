import pymongo
from __init__ import *
import os
import pandas as pd
import functools
import numpy as np


def check_errors(func):
    @functools.wraps(func)
    def wrapper_check_errors(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            print("error in " + str(func))
    return wrapper_check_errors


class Database:

    EMPTY_PLAYER = pd.DataFrame([], columns=["user_id", "tag", "username", "time_registered", "elo", "is_ranked", "staff"])
    EMPTY_MATCH = pd.DataFrame([], columns=["match_id", "time_started", "player_1", "player_2", "p1_declared", "p2_declared", "p1_elo", "p2_elo", "p1_is_ranked", "p2_is_ranked", "outcome", "staff_declared"])
    EMPTY_LOBBY = pd.DataFrame([], columns=["channel_id", "lobby_name", "roles", "player", "time_joined"])

    DEFAULT_CONFIG = pd.Series(index=["results_channel", "staff_role"], dtype="float64").replace(np.nan, None)
    EMPTY_ELO_ROLES = pd.DataFrame([], columns=["role", "elo_min", "elo_max", "priority"])

    players_tbl = "players"
    matches_tbl = "matches"
    queues_tbl = "queues"
    config_tbl = "config"
    elo_roles_tbl = "elo_roles"

    required_tables = [players_tbl, matches_tbl, queues_tbl, config_tbl, elo_roles_tbl]

    def __init__(self, guild_id):
        url = os.environ.get("MONGODB_URL")
        client = pymongo.MongoClient(url)

        self.guild_name = str(guild_id)

        if guild_id == PROJECT_X:
            self.guild_name = "PX"
        elif guild_id == TESTING_GUILD_ID:
            self.guild_name = "testing"

        self.guildDB = client["guild_" + self.guild_name]


    def setup_test(self): #always called at the start

        player_id = np.array([623257053879861248])[0]
        num_matches=4

        elo_roles = self.get_config()
        print("before\n", elo_roles)
        elo_roles["role"] = 32432
        self.upsert_config(elo_roles)
        elo_roles = self.get_config()
        print("after", elo_roles)
        pass

    def init_database(self):
        existing_tables = self.guildDB.list_collection_names()
        for i in self.required_tables:
            if i in existing_tables:
                continue
            self.guildDB.create_collection(i)

    #get always returns a properly formatted series or DF, even if there doesn't exist one. can pass a series from these to upsert __. An empty series works

    def get_players(self, user_id=None, staff=None, top_by_elo=None) -> pd.DataFrame:

        #dataframe of all players
        cur_filter = {}
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
        full_players_df = pd.concat([self.EMPTY_PLAYER, players_df])[self.EMPTY_PLAYER.columns].replace(np.nan, None)
        return full_players_df.reset_index(drop=True)

    def get_new_player(self, user_id) -> pd.Series:
        new_player = pd.concat([self.EMPTY_PLAYER, pd.DataFrame([[user_id]], columns=["user_id"])]).iloc[0]
        return new_player

    def upsert_player(self, player:pd.Series): #takes a series returned from get_players or new_player

        player = player.replace(np.nan, None)

        player["user_id"] = int(player["user_id"])
        if player["staff"] is not None:
            player["staff"] = int(player["staff"])
        if player["elo"] is not None:
            player["elo"] = float(player["elo"])

        playerdict = player.to_dict()
        self.guildDB[self.players_tbl].update_one({"user_id":playerdict["user_id"]}, {"$set":playerdict}, upsert=True)

    def upsert_players(self, players:pd.DataFrame):
        for i in players.index:
            self.upsert_player(players.iloc[i])


    def get_matches(self, user_id=None, match_id=None, number=1, from_first=False) -> pd.DataFrame:

        cur_filter = {}
        if user_id:
            user_id = int(user_id)
            cur_filter["$or"] = [{"player_1":user_id}, {"player_2":user_id}]

        if match_id:
            match_id = int(match_id)
            cur_filter["match_id"] = match_id

        sort_order = 1 if from_first else -1
        cur = self.guildDB[self.matches_tbl].find(cur_filter, projection={"_id":False}).sort("match_id", sort_order) #sort by match_id, descending
        if number:
            cur.limit(number)

        matches_df = pd.DataFrame(list(cur))
        full_matches_df = pd.concat([self.EMPTY_MATCH, matches_df])[self.EMPTY_MATCH.columns].replace(np.nan, None)
        return full_matches_df.reset_index(drop=True)

    def get_new_match(self) -> pd.Series:

        prev_match = self.get_matches(number=1)
        if prev_match.empty:
            new_id = 0
        else:
            new_id = prev_match.iloc[0]["match_id"] + 1

        match_df = pd.DataFrame([[new_id]], columns=["match_id"])
        new_match = pd.concat([self.EMPTY_MATCH, match_df]).iloc[0]
        return new_match

    def upsert_match(self, match:pd.Series):
        match = match.replace(np.nan, None) #all DB updates should go throughh this. this takes care of fixing the types

        self.EMPTY_MATCH #Make sure nothing is numpy type
        match["match_id"] = int(match["match_id"])
        if match["player_1"] is not None:
            match["player_1"] = int(match["player_1"])
        if match["player_2"] is not None:
            match["player_2"] = int(match["player_2"])

        matchdict = match.to_dict()
        self.guildDB[self.matches_tbl].update_one({"match_id":matchdict["match_id"]}, {"$set":matchdict}, upsert=True)


    def get_queues(self, channel_id = None) -> pd.DataFrame:
        cur_filter = {}
        if channel_id:
            cur_filter["channel_id"] = int(channel_id)

        cur = self.guildDB[self.queues_tbl].find(cur_filter, projection={"_id":False})

        queues_df =  pd.DataFrame(list(cur))
        updated_queues_df = pd.concat([self.EMPTY_LOBBY, queues_df])[self.EMPTY_LOBBY.columns].replace(np.nan, None)
        return updated_queues_df.reset_index(drop=True)

    def get_new_queue(self, channel_id) -> pd.Series:
        queue = pd.Series([channel_id], index=["channel_id"])
        new_queue = pd.concat([self.EMPTY_LOBBY, pd.DataFrame(queue).T]).iloc[0]
        return new_queue

    def upsert_queue(self, queue:pd.Series): # only pass something returned from new_queue or get_queue
        queue = queue.replace(np.nan, None)

        self.EMPTY_LOBBY #Make sure nothning is numpy type
        if queue["channel_id"] is not None:
            queue["channel_id"] = int(queue["channel_id"])
        if queue["player"] is not None:
            queue["player"] = int(queue["player"])
        try:
            print(queue)
            queue["roles"] = np.array(queue["roles"]).astype("int64").tolist()
        except:
            pass

        queuedict = queue.to_dict()
        self.guildDB[self.queues_tbl].update_one({"channel_id":queuedict["channel_id"]}, {"$set":queuedict}, upsert=True)

    def remove_queue(self, queue:pd.Series):
        channel_id = queue["channel_id"]

        self.guildDB[self.queues_tbl].delete_one({"channel_id":channel_id})


    def get_config(self) -> pd.Series:
        cur = self.guildDB[self.config_tbl].find({}, projection={"_id":False})

        if cur is None:
            self.upsert_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG

        return pd.Series(cur[0])

    def upsert_config(self, config:pd.Series): # takes a series returned from get_config
        configdict = config.to_dict()
        # print("configdict:\n", config, "\n",configdict)
        self.guildDB[self.config_tbl].update_one({}, {"$set":configdict}, upsert=True)

    def upsert_elo_roles(self, elo_roles_df:pd.DataFrame):
        self.guildDB[self.elo_roles_tbl].update_many({}, {"$set":elo_roles_df.to_dict("tight")}, upsert=True)

    def get_elo_roles(self) -> pd.DataFrame:
        cur = self.guildDB[self.elo_roles_tbl].find_one()

        if cur is None:
            df = pd.DataFrame.to_dict(self.EMPTY_ELO_ROLES, orient="tight")
            df = pd.DataFrame.from_dict(df, orient="tight")
            self.upsert_elo_roles(self.EMPTY_ELO_ROLES)
            return df

        elo_roles_df = pd.DataFrame.from_dict(cur, orient="tight")
        elo_roles_df = pd.concat([self.EMPTY_ELO_ROLES, elo_roles_df]).replace(np.nan, None)
        return elo_roles_df.reset_index(drop=True)
