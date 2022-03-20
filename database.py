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

    EMPTY_PLAYER = pd.DataFrame([], columns=["user_id", "username", "time_registered", "elo"])
    EMPTY_MATCH = pd.DataFrame([], columns=["match_id", "time_started", "player_1", "player_2", "p1_declared", "p2_declared", "p1_elo", "p2_elo", "outcome"])
    EMPTY_QUEUE = pd.DataFrame([], columns=["channel_id", "lobby_name", "roles", "player", "time_joined"])
    EMPTY_CONFIG = pd.DataFrame([], columns=["_", "staff_roles", "results_channel"])


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

        # self.guildDB.create_collection("temp")


        # self.guildDB["temp"].update_one()
        p = np.array([234923942380808098, 230482048239808])

        s = pd.Series([p, 423998797238948732], index=["a", "b"])
        d = s.to_dict()
        print(type(d["a"]))

        self.add_new_match()

        # if type(p).__module__ == np.__name__:
        #     p = p.item()
        # id= self.get_queues(953690285035098142).loc[0]["player"]
        # id = int(id)
        # print(type(id))
        # cur = self.guildDB[self.players_tbl].find({"user_id":id})
        # print(cur[0])

        self.get_players()



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


    def get_players(self, user_id=None, by_elo=False, from_to=None) -> pd.DataFrame:
        cur_filter = {}

        if user_id:
            user_id = int(user_id)
            cur_filter["user_id"] = user_id

        cur = self.guildDB[self.players_tbl].find(cur_filter)

        if by_elo:
            cur.sort("elo", -1)

        if from_to is None:
            from_to = [0, 1]

        cur.skip(from_to[0])
        cur.limit(from_to[1])

        return pd.DataFrame(cur[:]).drop("_id", errors="ignore")

    def get_matches(self, user_id=None, number=1) -> pd.DataFrame:

        cur_filter = {}
        if user_id:
            user_id = int(user_id)
            cur_filter["$or"] = [{"player_1":user_id},{"player_2":user_id}]

        cur = self.guildDB[self.matches_tbl].find(cur_filter).sort("match_id", -1).limit(number)

        return pd.DataFrame(cur[:]).drop("_id", errors="ignore")

    def get_queues(self, channel_id) -> pd.DataFrame:
        cur_filter = {}
        if channel_id:
            channel_id = int(channel_id)  #mongo db doesn't recognize numpy.Int64 for some reason
            cur_filter["channel_id"] = channel_id

        print(channel_id)
        cur = self.guildDB[self.queues_tbl].find(cur_filter)
        return pd.DataFrame(cur[:]).drop("_id", errors="ignore")


    def upsert_player(self, player:pd.Series):

        playerdict = player.fillna(0).to_dict()

        result = self.guildDB[self.players_tbl].update_one({"user_id":playerdict["user_id"]}, {"$set":playerdict}, upsert=True)
        updated_existing = result.raw_result["updatedExisting"]

    def upsert_match(self, match:pd.Series): #puts first row of dataframe in match

        matchdict = match.fillna(0).to_dict()

        result = self.guildDB[self.matches_tbl].update_one({"match_id":matchdict["match_id"]}, {"$set":matchdict}, upsert=True)
        updated_existing = result.raw_result["updatedExisting"]

    def upsert_queue(self, queue:pd.Series):

        queue["roles"] = list(queue["roles"]) #mongo doesn't accept int64
        queuedict = queue.fillna(0).to_dict()

        result = self.guildDB[self.queues_tbl].update_one({"channel_id":queuedict["channel_id"]}, {"$set":queuedict}, upsert=True)
        updated_existing = result.raw_result["updatedExisting"]


    #above: worry about converting numpy to native python

    def add_new_player(self, user_id, **kwargs):

        player = pd.Series()

        player["user_id"] = user_id
        for k in kwargs:
            if k in self.EMPTY_PLAYER.columns:
                player[k] = kwargs[k]
            else:
                raise Exception("Invalid column for player:" + str(k))

        new_player = pd.concat([self.EMPTY_PLAYER, pd.DataFrame(player).T]).fillna(0)
        self.upsert_player(new_player)

    def add_new_match(self, **kwargs):
        prev_match = self.get_matches()
        if prev_match.empty:
            new_id = 0
        else:
            new_id = prev_match.iloc[0]["match_id"] + 1

        match = pd.Series()
        match["match_id"] = new_id
        for k in kwargs:
            if k in self.EMPTY_MATCH.columns:
                match[k] = kwargs[k]
            else:
                raise Exception("Invalid column for match:" + str(k))

        new_match = pd.concat([self.EMPTY_MATCH, pd.DataFrame(match).T]).fillna(0).iloc[0]
        print(new_match)
        self.upsert_match(new_match)

    def add_new_queue(self, channel_id, **kwargs):

        queue = pd.Series()
        queue["channel_id"] = channel_id

        for k in kwargs:
            if k in self.EMPTY_QUEUE.columns:
                queue[k] = kwargs[k]
            else:
                raise Exception("Invalid column for queue:" + str(k))

        queue = queue.fillna(0)

        new_queue = pd.concat([self.EMPTY_QUEUE, pd.DataFrame(queue).T]).fillna(0).iloc[0]
        self.upsert_queue(new_queue)
