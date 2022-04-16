import os
from typing import List
from enum import Enum
import time

import numpy as np
import pandas as pd
import pymongo
import alluka

from Challenger.config import Database_Config


from .temp import client

class Client(pymongo.MongoClient):

    def __init__(self):

        start = time.perf_counter()
        url = os.environ.get("MONGODB_URL")
        super().__init__(url)
        print("Time taken to connect to mongo client", time.perf_counter()- start)

        client.append(self)
        print(client)



class Session:

    empty_player_df = pd.DataFrame([], columns=["user_id", "tag", "username", "time_registered", "elo", "is_ranked"]).set_index("user_id")

    empty_match_df = pd.DataFrame([], columns=[
        "match_id", "time_started", "outcome", "staff_declared",
        "p1_id", "p1_elo", "p1_elo_after", "p1_declared", "p1_is_ranked", "p1_is_ranked_after",
        "p2_id", "p2_elo", "p2_elo_after", "p2_declared", "p2_is_ranked", "p2_is_ranked_after"])\
        .set_index("match_id")

    empty_lobby_df = pd.DataFrame([], columns=["channel_id", "lobby_name", "required_role", "player", "time_joined"])


    #these are structured differently
    empty_elo_roles = pd.DataFrame([], columns=["role", "elo_min", "elo_max", "priority"])
    empty_config = pd.Series(index=["results_channel", "staff_role", "guild_name"], dtype="float64").replace(np.nan, None)
    empty_config_df = pd.DataFrame([], columns=["guild_name", "default_results_channel", "staff_role"]) #TODO use this

    class tbl_names(Enum):
        PLAYERS = "players"
        MATCHES = "matches"
        LOBBIES = "lobbies"
        CONFIG = "config"
        ELO_ROLES = "elo_roles"


    def __init__(self, guild_id):

        print(client)
        if len(client) == 0:
            self.client = Client()
        else:
            self.client = client[0]

        self.guild_id = guild_id

        if guild_id in Database_Config.KNOWN_GUILDS:
            self.guild_identifier = Database_Config.KNOWN_GUILDS[guild_id] # this is a unique name for the guild in the database
        else:
            self.guild_identifier = str(guild_id)

        self.guildDB = self.client["guild_" + self.guild_identifier]


    def test(self):
        pass


    def create_collections(self):

        #update the guild's name in the db


        #make sure all required collections exist in this guild's database
        existing_tables = self.guildDB.list_collection_names()
        for i in self.tbl_names:

            if not i.value in existing_tables:
                self.guildDB.create_collection(i.value)


    def delete_database(self):
        self.client.drop_database(self.guildDB.name)



    #get always returns a properly formatted series or DF, even if there doesn't exist one. can pass a series from these to upsert __. An empty series works

    def get_players(self, user_id=None, user_ids: List =None, staff=None, top_by_elo=None) -> pd.DataFrame:

        #dataframe of all players
        cur_filter = {}
        if user_ids is not None:
            cur_filter["user_id"] = {"$in": user_ids}
        if user_id:
            cur_filter["user_id"] = int(user_id)
        if staff:
            cur_filter["staff"] = staff

        cur = self.guildDB[self.tbl_names.PLAYERS.value].find(cur_filter, projection={"_id":False})

        if top_by_elo:
            cur.sort("elo", -1)
            cur.skip(top_by_elo[0])
            cur.limit(top_by_elo[1])

        players_df = pd.DataFrame(list(cur))
        if not players_df.empty:
            players_df.set_index("user_id", inplace=True)
        full_players_df = pd.concat([self.empty_player_df, players_df])[self.empty_player_df.columns].replace(np.nan, None)
        return full_players_df

    def get_new_player(self, user_id) -> pd.Series:
        player_df = pd.DataFrame([[user_id]], columns=["user_id"]).set_index("user_id")
        new_player = pd.concat([self.empty_player_df, player_df]).iloc[0]
        return new_player

    def upsert_player(self, player:pd.Series): #takes a series returned from get_players or new_player

        player = player.replace(np.nan, None)

        player["user_id"] = int(player.name)
        if player["elo"] is not None:
            player["elo"] = float(player["elo"])

        playerdict = player.to_dict()
        self.guildDB[self.tbl_names.PLAYERS.value].update_one({"user_id":playerdict["user_id"]}, {"$set":playerdict}, upsert=True)

    def upsert_players(self, players:pd.DataFrame):
        for i, row in players.iterrows():
            self.upsert_player(row)



    def get_matches(self, user_id=None, match_id=None, number=None, skip=0, increasing=False) -> pd.DataFrame:
        """
        Params
        ------
        user_id: int
            if specified gets all matches where the user is involved
        match_id: int
            if match_id is specified, returns the match with that id
        increasing: if true, returns matches from oldest to newest
        """

        print("from guild: " + self.guild_identifier)

        cur_filter = {}
        if user_id is not None:
            user_id = int(user_id)
            cur_filter["$or"] = [{"p1_id":user_id}, {"p2_id":user_id}]
            print(cur_filter)

        if match_id is not None:
            match_id = int(match_id)
            cur_filter["match_id"] = match_id

        sort_order = 1 if increasing else -1
        cur = self.guildDB[self.tbl_names.MATCHES.value].find(cur_filter, projection={"_id":False}).sort("match_id", sort_order).skip(skip)

        if number is not None:
            cur.limit(number) #TODO: always limit to 100 or so, if needed

        matches_df = pd.DataFrame(list(cur), dtype="object")
        if not matches_df.empty:
            matches_df.set_index("match_id", inplace=True)
        full_matches_df = pd.concat([self.empty_match_df, matches_df])[self.empty_match_df.columns].replace(np.nan, None)
        return full_matches_df

    def get_new_match(self) -> pd.Series:

        prev_match = self.get_matches(number=1)
        if prev_match.empty:
            new_id = 1
        else:
            new_id = prev_match.index.max() + 1

        match_df = pd.DataFrame([[new_id]], columns=["match_id"]).set_index("match_id")
        new_match = pd.concat([self.empty_match_df, match_df]).iloc[0]
        return new_match

    def upsert_match(self, match:pd.Series):
        match = match.copy()
        match["match_id"] = match.name #match_id is the index of the match
        match = match.replace(np.nan, None) #replace nan with none fixes the types. set dtype to object

        match["match_id"] = int(match["match_id"])
        if match["p1_id"] is not None:
            match["p1_id"] = int(match["p1_id"])
        if match["p2_id"] is not None:
            match["p2_id"] = int(match["p2_id"])

        matchdict = match.to_dict()
        self.guildDB[self.tbl_names.MATCHES.value].update_one({"match_id":matchdict["match_id"]}, {"$set":matchdict}, upsert=True)

    def upsert_matches(self, matches:pd.DataFrame):
        for i in matches.index:
            self.upsert_match(matches.loc[i])

    def delete_all_matches(self):
        self.guildDB[self.tbl_names.MATCHES.value].delete_many({})



    def get_lobbies(self, channel_id = None) -> pd.DataFrame:
        cur_filter = {}
        if channel_id is not None:
            cur_filter["channel_id"] = int(channel_id)

        cur = self.guildDB[self.tbl_names.LOBBIES.value].find(cur_filter, projection={"_id":False})

        queues_df =  pd.DataFrame(list(cur))
        updated_queues_df = pd.concat([self.empty_lobby_df, queues_df])[self.empty_lobby_df.columns].replace(np.nan, None)
        return updated_queues_df.reset_index(drop=True)

    def get_new_lobby(self, channel_id) -> pd.Series:
        queue = pd.Series([channel_id], index=["channel_id"])
        new_queue = pd.concat([self.empty_lobby_df, pd.DataFrame(queue).T]).iloc[0]
        return new_queue

    def upsert_lobby(self, queue:pd.Series): # only pass something returned from new_queue or get_queue
        queue = queue.replace(np.nan, None)

        self.empty_lobby_df #Make sure nothning is numpy type
        if queue["channel_id"] is not None:
            queue["channel_id"] = int(queue["channel_id"])
        if queue["player"] is not None:
            queue["player"] = int(queue["player"])
        if queue["required_role"] is not None:
            queue["required_role"] = int(queue["required_role"])

        required_role = 1

        queuedict = queue.to_dict()
        self.guildDB[self.tbl_names.LOBBIES.value].update_one({"channel_id":queuedict["channel_id"]}, {"$set":queuedict}, upsert=True)

    def remove_lobby(self, channel_id):
        self.guildDB[self.tbl_names.LOBBIES.value].delete_one({"channel_id":channel_id})



    def get_config(self) -> pd.Series:
        if self.guildDB[self.tbl_names.CONFIG.value].count_documents({}) == 0:
            self.upsert_config(self.empty_config)
            return self.get_config()

        cur = self.guildDB[self.tbl_names.CONFIG.value].find({}, projection={"_id":False})

        return pd.Series(cur[0], dtype="object").replace(np.nan, None)

    def upsert_config(self, config:pd.Series): # takes a series returned from get_config
        configdict = config.to_dict()
        self.guildDB[self.tbl_names.CONFIG.value].update_one({}, {"$set":configdict}, upsert=True)


    def upsert_elo_roles(self, elo_roles_df:pd.DataFrame):
        self.guildDB[self.tbl_names.ELO_ROLES.value].update_many({}, {"$set":elo_roles_df.to_dict("tight")}, upsert=True)

    def get_elo_roles(self) -> pd.DataFrame:
        cur = self.guildDB[self.tbl_names.ELO_ROLES.value].find_one()

        if cur is None:
            df = pd.DataFrame.to_dict(self.empty_elo_roles, orient="tight")
            df = pd.DataFrame.from_dict(df, orient="tight")
            self.upsert_elo_roles(self.empty_elo_roles)
            return df

        elo_roles_df = pd.DataFrame.from_dict(cur, orient="tight")
        elo_roles_df = pd.concat([self.empty_elo_roles, elo_roles_df]).replace(np.nan, None)
        return elo_roles_df.reset_index(drop=True)

