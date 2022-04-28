import os
from typing import List
from enum import Enum
import time

import bson
import numpy as np
import pandas as pd
import pymongo
import mongoengine as me

from Challenger.config import Database_Config
from Challenger.utils import *




class User(me.Document):
    """
    Collection
    Global user, can be in multiple leaderboards and guilds
    """
    user_id = me.IntField(primary_key=True)
    username = me.StringField()
    nickname= me.StringField()

    meta = {'collection': 'users'}



class Player(me.EmbeddedDocument):
    """
    Field in leaderboard
    """
    user = me.LazyReferenceField(User)
    time_registered = me.DateTimeField() # time.time()
    rating = me.FloatField()
    rating_deviation = me.FloatField()



class Match(me.EmbeddedDocument):
    """
    Field in Leaderboard
    """

    match_id = me.IntField()
    outcome = me.EnumField(Outcome)
    time_started = me.DateTimeField()

    player1_id = me.IntField()
    player1_declared = me.EnumField(Declare)
    player1_elo = me.FloatField()
    player1_RD = me.FloatField()

    player2_id = me.IntField()
    player2_declared = me.EnumField(Declare)
    player2_elo = me.FloatField()
    player2_RD = me.FloatField()



class Lobby(me.EmbeddedDocument):
    """
    Field in Leaderboard, which is a field in Guild
    """
    channel_id = me.IntField(required=True)
    name = me.StringField()
    user_in_q = me.LazyReferenceField(User)
    elo_range = me.ListField(me.FloatField())
    updates_channel = me.IntField()


class Leaderboard(me.EmbeddedDocument):
    """
    Field in Guild
    """
    name = me.StringField()
    players = me.EmbeddedDocumentListField(Player)
    matches = me.EmbeddedDocumentListField(Match)
    lobbies = me.EmbeddedDocumentListField(Lobby)
    elo_roles = me.DictField()


class Global_Leaderboard(me.Document):
    """
    Collection
    Global leaderboard, can be in multiple guilds
    """
    leaderboard = me.EmbeddedDocumentField(Leaderboard)
    meta = {'collection': 'global_leaderboards'}



class Guild(me.Document):
    """
    Collection
    """
    guild_id = me.IntField(primary_key=True)
    name = me.StringField()
    admin_role_id = me.IntField()
    staff_role_id = me.IntField()
    leaderboards = me.EmbeddedDocumentListField(Leaderboard)

    meta = {'collection': 'guilds'}




class Mongo_Client(pymongo.MongoClient):

    def __init__(self):

        url = os.environ.get("MONGODB_URL")

        start = time.perf_counter()
        super().__init__(url)
        print("Time taken to connect to mongo client", time.perf_counter()-start)


class Guild_DB:

    empty_player_df = pd.DataFrame([], columns=["user_id", "tag", "username", "time_registered", "elo", "is_ranked"]).set_index("user_id")

    empty_match_df = pd.DataFrame([], columns=[
        "match_id", "time_started", "outcome", "staff_declared",
        "p1_id", "p1_elo", "p1_elo_after", "p1_declared", "p1_is_ranked", "p1_is_ranked_after",
        "p2_id", "p2_elo", "p2_elo_after", "p2_declared", "p2_is_ranked", "p2_is_ranked_after"])\
        .set_index("match_id")

    empty_lobby_df = pd.DataFrame([], columns=["channel_id", "leaderboard", "lobby_name", "required_role", "player"])
    empty_elo_roles = pd.DataFrame([], columns=["role_id", "min_elo", "max_elo"]).set_index("role_id")


    #these are structured differently
    empty_config = pd.Series(index=["results_channel", "staff_role", "guild_name"], dtype="float64").replace(np.nan, None)

    class tbl_names(Enum):
        PLAYERS = "players"
        MATCHES = "matches"
        LOBBIES = "lobbies"
        CONFIG = "config"
        ELO_ROLES = "elo_roles"

    leaderboards = []


    def __init__(self, guild_id):

        if Database_Config.mongodb_client is None:
            Database_Config.mongodb_client = Mongo_Client()
        self.client = Database_Config.mongodb_client


        self.guild_id = guild_id

        if guild_id in Database_Config.KNOWN_GUILDS:
            self.guild_identifier = Database_Config.KNOWN_GUILDS[guild_id] # this is a unique name for the guild in the database
        else:
            self.guild_identifier = str(guild_id)

        self.guildDB = self.client["guild_" + self.guild_identifier]


    def test(self):
        self.guildDB = self.client["guild_pela"]

        players = self.get_players(by_elo=True, ranked=True, skip=2, limit=2)

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

    def get_players(self, user_id=None, user_ids:List =None, staff=None, limit=None, skip=0, by_elo:bool=False, ranked:bool=None) -> pd.DataFrame:

        """
        params applied in this order: by_elo/ranked, skip, limit
        """

        #dataframe of all players
        cur_filter = {}
        if user_ids is not None:
            cur_filter["user_id"] = {"$in": user_ids}
        if user_id is not None:
            cur_filter["user_id"] = int(user_id)
        if staff:
            cur_filter["staff"] = staff
        if ranked is not None:
            cur_filter["is_ranked"] = ranked

        cur = self.guildDB[self.tbl_names.PLAYERS.value].find(cur_filter, projection={"_id":False})

        if by_elo:
            cur.sort("elo", -1)

        cur.skip(skip)

        if limit is not None:
            cur.limit(limit)

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

    def delete_player(self, user_id):
        self.guildDB[self.tbl_names.PLAYERS.value].delete_one({"user_id":user_id})

    def delete_all_players(self):
        self.guildDB[self.tbl_names.PLAYERS.value].delete_many({})



    def get_matches(self, user_id=None, match_id=None, limit=None, skip=0, chronological=False) -> pd.DataFrame:
        """
        Params
        ------
        user_id: int
            if specified gets all matches where the user is involved
        match_id: int
            if match_id is specified, returns the match with that id
        increasing: if true, returns matches from oldest to newest
        """

        cur_filter = {}
        if user_id is not None:
            user_id = int(user_id)
            cur_filter["$or"] = [{"p1_id":user_id}, {"p2_id":user_id}]

        if match_id is not None:
            match_id = int(match_id)
            cur_filter["match_id"] = match_id

        sort_order = 1 if chronological else -1
        cur = self.guildDB[self.tbl_names.MATCHES.value].find(cur_filter, projection={"_id":False}).sort("match_id", sort_order).skip(skip)

        if limit is not None:
            cur.limit(limit) #TODO: always limit to 100 or so, if needed

        matches_df = pd.DataFrame(list(cur), dtype="object")
        if not matches_df.empty:
            matches_df.set_index("match_id", inplace=True)
        full_matches_df = pd.concat([self.empty_match_df, matches_df])[self.empty_match_df.columns].replace(np.nan, None)
        return full_matches_df

    def get_new_match(self) -> pd.Series:

        prev_match = self.get_matches(limit=1)
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

    def delete_lobby(self, channel_id):
        self.guildDB[self.tbl_names.LOBBIES.value].delete_one({"channel_id":channel_id})

    def delete_all_lobbies(self):
        self.guildDB[self.tbl_names.LOBBIES.value].delete_many({})



    def upsert_elo_role(self, elo_role:pd.Series):
        elo_role = elo_role.copy()
        elo_role["role_id"] = elo_role.name
        elo_role = elo_role.replace(np.nan, None)

        elo_role_dict = elo_role.to_dict()
        self.guildDB[self.tbl_names.ELO_ROLES.value].update_one({"role_id":elo_role_dict["role_id"]}, {"$set":elo_role_dict}, upsert=True)

    def upsert_elo_roles(self, elo_roles_df:pd.DataFrame):
        for index, elo_role in elo_roles_df.iterrows():
            self.upsert_elo_role(elo_role)

    def get_elo_roles(self) -> pd.DataFrame:

        cur = self.guildDB[self.tbl_names.ELO_ROLES.value].find(projection={"_id":False})

        elo_roles_df = pd.DataFrame(list(cur), dtype="object")

        if not elo_roles_df.empty:
            elo_roles_df.set_index("role_id", inplace=True)

        full_elo_roles_df = pd.concat([self.empty_elo_roles, elo_roles_df])[self.empty_elo_roles.columns].replace(np.nan, None)
        return full_elo_roles_df

    def delete_elo_role(self, role_id):
        self.guildDB[self.tbl_names.ELO_ROLES.value].delete_one({"role_id":role_id})



    def get_config(self) -> pd.Series:
        if self.guildDB[self.tbl_names.CONFIG.value].count_documents({}) == 0:
            self.upsert_config(self.empty_config)
            return self.get_config()

        cur = self.guildDB[self.tbl_names.CONFIG.value].find({}, projection={"_id":False})

        return pd.Series(cur[0], dtype="object").replace(np.nan, None)

    def upsert_config(self, config:pd.Series): # takes a series returned from get_config
        configdict = config.to_dict()
        self.guildDB[self.tbl_names.CONFIG.value].update_one({}, {"$set":configdict}, upsert=True)

