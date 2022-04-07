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

    EMPTY_PLAYER = pd.DataFrame([], columns=["user_id", "tag", "username", "time_registered", "elo", "is_ranked", "matches", "staff"])
    EMPTY_MATCH = pd.DataFrame([], columns=["match_id", "time_started", "player_1", "player_2", "p1_declared", "p2_declared", "p1_elo", "p2_elo", "p1_is_ranked", "p2_is_ranked", "outcome", "staff_declared"])
    EMPTY_LOBBY = pd.DataFrame([], columns=["channel_id", "lobby_name", "roles", "player", "time_joined"])

    EMPTY_CONFIG = pd.DataFrame([], columns=["results_channel", "roles_by_elo", "staff_role"])

    players_tbl = "players"
    matches_tbl = "matches"
    queues_tbl = "queues"
    config_tbl = "config"

    required_tables = [players_tbl, matches_tbl, queues_tbl, config_tbl]

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

        player_id = 623257053879861248
        num_matches=4

        matches = self.get_matches(user_id=player_id, number=num_matches, ascending=True)
        # print(matches)
        pass

    def init_database(self):
        existing_tables = self.guildDB.list_collection_names()
        for i in self.required_tables:
            if i in existing_tables:
                continue
            self.guildDB.create_collection(i)
            if i == self.config_tbl:
                config = self.get_config()
                self.upsert_config(config)

    #get always returns a properly formatted series or DF, even if there doesn't exist one. can pass a series from these to upsert __. An empty series works

    def get_players(self, user_id=None, staff=None, top_by_elo=None) -> pd.DataFrame:
        cur_filter = {}

        if user_id:
            user_id = int(user_id)
            cur_filter["user_id"] = user_id
        if staff:
            cur_filter["staff"] = staff

        cur = self.guildDB[self.players_tbl].find(cur_filter)

        if top_by_elo:
            cur.sort("elo", -1)
            cur.skip(top_by_elo[0])
            cur.limit(top_by_elo[1])

        players_df = pd.DataFrame(list(cur)).drop("_id", axis=1, errors="ignore")
        updated_players_df = pd.concat([self.EMPTY_PLAYER, players_df]).replace(np.nan, None)
        return updated_players_df

    def get_new_player(self, user_id) -> pd.Series:
        player = pd.Series([user_id], index=["user_id"])
        new_player = pd.concat([self.EMPTY_PLAYER, pd.DataFrame(player).T]).iloc[0]
        return new_player

    def get_matches(self, user_id=None, match_id=None, number=None, ascending=False) -> pd.DataFrame:

        cur_filter = {}
        if user_id:
            user_id = int(user_id)
            cur_filter["$or"] = [{"player_1":user_id},{"player_2":user_id}]

        if match_id:
            match_id = int(match_id)
            cur_filter["match_id"] = match_id

        sort_order = 1 if ascending else -1

        cur = self.guildDB[self.matches_tbl].find(cur_filter).sort("match_id", sort_order) #sort by match_id, descending
        if number:
            cur.limit(number)
        matches_df = pd.DataFrame(list(cur)).drop("_id", axis=1, errors="ignore")
        updated_matches = pd.concat([self.EMPTY_MATCH, matches_df]).replace(np.nan, None)
        return updated_matches

    def get_new_match(self) -> pd.Series:

        prev_match = self.get_matches()
        if prev_match.empty:
            new_id = 0
        else:
            new_id = prev_match.iloc[0]["match_id"] + 1

        match = pd.Series([new_id], index=["match_id"])
        new_match = pd.concat([self.EMPTY_MATCH, pd.DataFrame(match).T]).iloc[0]

        return new_match


    def get_queues(self, channel_id = None) -> pd.DataFrame:
        cur_filter = {}
        if channel_id:
            channel_id = int(channel_id)  #mongo db doesn't recognize numpy.Int64 for some reason
            cur_filter["channel_id"] = channel_id

        cur = self.guildDB[self.queues_tbl].find(cur_filter)
        queue_df =  pd.DataFrame(list(cur)).drop("_id", axis=1, errors="ignore")
        updated_queues = pd.concat([self.EMPTY_LOBBY, queue_df]).replace(np.nan, None)
        return updated_queues


    def get_new_queue(self, channel_id) -> pd.Series:
        queue = pd.Series([channel_id], index=["channel_id"])
        new_queue = pd.concat([self.EMPTY_LOBBY, pd.DataFrame(queue).T]).iloc[0]
        return new_queue

    def get_config(self) -> pd.Series:
        cur = self.guildDB[self.config_tbl].find()
        df = pd.DataFrame(list(cur)).drop("_id", axis=1, errors="ignore")

        if not df.empty:
            ret = df.iloc[0]
            ret["roles_by_elo"] = pd.DataFrame.from_dict(ret["roles_by_elo"], orient="tight")
            return ret
        else:
            config = pd.DataFrame([[pd.DataFrame([], columns=["priority", "min", "max"])]], columns=["roles_by_elo"])
            config_df = pd.concat([self.EMPTY_CONFIG, config]).iloc[0]
            self.upsert_config(config_df)
            return self.get_config()


    #Above: standard. Change everything else to match it


    def upsert_player(self, player:pd.Series): #only pass something returned from get_players or new_player

        player = player.replace(np.nan, None)

        self.EMPTY_PLAYER #Make sure nothing is numpy type
        player["user_id"] = int(player["user_id"])
        if player["staff"] is not None:
            player["staff"] = int(player["staff"])
        if player["elo"] is not None:
            player["elo"] = float(player["elo"])

        playerdict = player.to_dict()
        self.guildDB[self.players_tbl].update_one({"user_id":playerdict["user_id"]}, {"$set":playerdict}, upsert=True)


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



    def upsert_config(self, config:pd.Series):
        """
            Only pass a series returned from get_config
        """

        config = config.replace(np.nan, None)

        self.EMPTY_CONFIG #make sure nothing is a numpy type
        # if config["roles_by_elo"] is None:
        #     rbe_df = pd.DataFrame([], columns=["min", "max", "priority"])
        #     rbe_df.index.name = "role"
        #     config["roles_by_elo"] = rbe_df

        configdict = config.to_dict()
        configdict["roles_by_elo"] = configdict["roles_by_elo"].to_dict("tight") #bson.errors.InvalidDocument: cannot encode object: Empty DataFrame

        self.guildDB[self.config_tbl].update_one({}, {"$set":configdict}, upsert=True)

