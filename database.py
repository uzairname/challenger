import time

import numpy as np
import pandas as pd
import pymongo

from __init__ import *
import os
from plugins.utils import *
from pymongo import MongoClient
from datetime import datetime


def check_errors(func):
    @functools.wraps(func)
    def wrapper_check_errors(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            print("error in " + str(func))
    return wrapper_check_errors

sample_queues = pd.DataFrame([["Lobby 1", 2489723947928, 0, 23947923749237, [23498723947239, 74658347952987]], ["Advanced Lobby", 0, 0, 6238423956834765, []]], columns=["lobby_name", "player_1", "player_2", "channel", "roles"])
sample_queues[["player_1", "player_2"]] = sample_queues[["player_1", "player_2"]].astype("Int64").fillna(0)
sample_queues.set_index("lobby_name")

sample_matches = pd.DataFrame([[1, 0, 3458934797, 238947239847, 0, 0, 50, 50],[3, 0, 6456458934797, 238947239847, 0, 0, 50, 30],[2, 0, 9653458934797, 239546847, 0, 0, 20, 53]], columns=["match_id", "time_started", "player_1", "player_2", "p1_declared", "p2_declared", "p1_elo", "p2_elo"])






class Database:

    players_columns=["user_id", "username", "time_registered", "elo"]
    matches_columns = ["match_id", "time_started", "player_1", "player_2", "p1_declared", "p2_declared", "p1_elo", "p2_elo"]
    queues_columns = ["channel_id", "lobby_name", "player_1", "player_2", "roles"]
    config_columns=["_", "staff_roles", "results_channel"]

    class player(pd.Series):
        def __init__(self, series:pd.Series, user_id, **kwargs):
            super().__init__(self, index=Database.players_columns, dtype=pd.Int64Dtype)
            self["user_id"] = user_id
            for k in kwargs:
                self[k] = kwargs[k]



    players_tbl = "players"
    matches_tbl = "matches"
    queues_tbl = "queues"
    config_tbl = "config"

    required_tables = [players_tbl, matches_tbl, queues_tbl, config_tbl]

    def __init__(self, guild_id):

        client = MongoClient("mongodb+srv://lilapela:CWahaG2nnNlOn74t@pelacluster.9oy7y.mongodb.net/pelaDB?retryWrites=true&w=majority")
        self.guild_name = str(guild_id)
        self.guildDB = client["guild_" + self.guild_name]


    def setup_test(self): #testing stuff is always called at the start, and can be called in guildstartingevent, to update DBs for every server

        # pdm.to_mongo(self.sample_queues, "queues_0", DB, if_exists="replace", index=False)
        queue = self.get_queue(234)
        print(queue)


        # queues_df = pdm.read_mongo("Collection1", [], "mongodb+srv://lilapela:CWahaG2nnNlOn74t@pelacluster.9oy7y.mongodb.net/pelaDB?retryWrites=true&w=majority")

        # from_mongo = pd.DataFrame(list(DB.find()))
        # print("from mongo:\n" + str(from_mongo) + "types: \n" + str(from_mongo.dtypes))

        # self.guildDB[self.matches_tbl].insert_many(sample_matches.to_dict("records"))
        #
        # new_player = self.player(user_id = 234897897, elo=40)
        # print(new_player)
        #
        # self.upsert_player(new_player)


    #insert/update: update_one. upsert

    #need getter and setter for every dataframe.

    def create_missing_tables(self):
        existing_tables = self.guildDB.list_collection_names()
        for i in self.required_tables:
            if i in existing_tables:
                continue
            self.guildDB.create_collection(i)


    def get_player(self, user_id) -> pd.DataFrame:
        cur = self.guildDB[self.players_tbl].find({"user_id": user_id}).limit(1)
        return pd.DataFrame(cur[:]).drop("_id", errors="ignore")

    def upsert_player(self, player:pd.DataFrame):
        playerdict = player.iloc[0].to_dict()
        result = self.guildDB[self.players_tbl].update_one({"user_id":playerdict["user_id"]}, {"$set":playerdict}, upsert=True)
        updated_existing = result.raw_result["updatedExisting"]


    def get_latest_matches(self, user_id=None, number=1) -> pd.DataFrame:
        cur_filter = {}
        if user_id:
            cur_filter["player_1"] = user_id

        cur = self.guildDB[self.matches_tbl].find(cur_filter).sort("match_id", -1).limit(number)

        return pd.DataFrame(cur[:]).drop("_id", errors="ignore")

    def upsert_match(self, match: pd.DataFrame): #puts first row of dataframe in match
        matchdict = match.iloc[0].to_dict()
        result = self.guildDB[self.matches_tbl].update_one({"match_id":matchdict["match_id"]}, {"$set":matchdict}, upsert=True)
        updated_existing = result.raw_result["updatedExisting"]


    def get_queue(self, channel_id):
        cur_filter = {"channel_id": channel_id}
        cur = self.guildDB[self.queues_tbl].find(cur_filter).limit(1)
        return pd.DataFrame(cur[:]).drop("_id", errors="ignore")

    def upsert_queue(self, queue: pd.DataFrame):
        queuedict = queue.iloc[0].to_dict()
        result = self.guildDB[self.queues_tbl].update_one({"channel_id":queuedict["channel_id"]}, {"$set":queuedict}, upsert=True)
        updated_existing = result.raw_result["updatedExisting"]
