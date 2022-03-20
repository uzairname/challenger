import pymongo
from __init__ import *
import os
from plugins.utils import *


def check_errors(func):
    @functools.wraps(func)
    def wrapper_check_errors(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            print("error in " + str(func))
    return wrapper_check_errors

# sample_queues = pd.DataFrame([["Lobby 1", 2489723947928, 0, 23947923749237, [23498723947239, 74658347952987]], ["Advanced Lobby", 0, 0, 6238423956834765, []]], columns=["lobby_name", "player_1", "player_2", "channel", "roles"])
# sample_queues[["player_1", "player_2"]] = sample_queues[["player_1", "player_2"]].astype("Int64").fillna(0)
# sample_queues.set_index("lobby_name")
#
# sample_matches = pd.DataFrame([[1, 0, 3458934797, 238947239847, 0, 0, 50, 50],[3, 0, 6456458934797, 238947239847, 0, 0, 50, 30],[2, 0, 9653458934797, 239546847, 0, 0, 20, 53]], columns=["match_id", "time_started", "player_1", "player_2", "p1_declared", "p2_declared", "p1_elo", "p2_elo"])



class Database:

    EMPTY_PLAYER = pd.DataFrame([], columns=["user_id", "username", "time_registered", "elo"])
    EMPTY_MATCH = pd.DataFrame([], columns=["match_id", "time_started", "player_1", "player_2", "p1_declared", "p2_declared", "p1_elo", "p2_elo", "outcome"])
    EMPTY_QUEUE = pd.DataFrame([], columns=["channel_id", "lobby_name", "roles", "player", "time_joined"])
    EMPTY_CONFIG = pd.DataFrame([], columns=["_", "staff_roles", "results_channel", "roles_by_elo"])
    CONFIG_FIRST_ROW = 0

    players_tbl = "players"
    matches_tbl = "matches"
    queues_tbl = "queues"
    config_tbl = "config"

    required_tables = [players_tbl, matches_tbl, queues_tbl, config_tbl]

    def __init__(self, guild_id):
        url = os.environ.get("MONGODB_URL")
        client = pymongo.MongoClient(url)

        self.guild_name = str(guild_id)
        if (guild_id == 947184983120957452):
            self.guild_name = "PX"
        self.guildDB = client["guild_" + self.guild_name]


    def setup_test(self): #always called at the start

        # pdm.to_mongo(self.sample_queues, "queues_0", DB, if_exists="replace", index=False)

        # self.guildDB.create_collection("temp")


        # self.guildDB["temp"].update_one()

        # a = self.get_players(top_by_elo=[1,1])

        elo_to_roles = pd.DataFrame([[0,100], [50,100]], columns=["min", "max"], index=[951233553360891924, 53894797823478723])

        self.add_new_config(roles_by_elo = elo_to_roles)

        from_mongo = self.get_config()

        print("from mongo: \n" + str(from_mongo) + "\n\n" + str(from_mongo["roles_by_elo"]))



        pass


    #insert/update: update_one. upsert

    #need getter and setter for every dataframe.

    def create_missing_tables(self):
        existing_tables = self.guildDB.list_collection_names()
        for i in self.required_tables:
            if i in existing_tables:
                continue
            self.guildDB.create_collection(i)

    def get_players(self, user_id=None, top_by_elo=None) -> pd.DataFrame:
        cur_filter = {}

        if user_id:
            user_id = int(user_id)
            cur_filter["user_id"] = user_id

        cur = self.guildDB[self.players_tbl].find(cur_filter)

        if top_by_elo:
            cur.sort("elo", -1)
            cur.skip(top_by_elo[0])
            cur.limit(top_by_elo[1])

        return pd.DataFrame(list(cur)).drop("_id", axis=1, errors="ignore")


    def get_matches(self, user_id=None, number=1) -> pd.DataFrame:

        cur_filter = {}
        if user_id:
            user_id = int(user_id)
            cur_filter["$or"] = [{"player_1":user_id},{"player_2":user_id}]

        cur = self.guildDB[self.matches_tbl].find(cur_filter).sort("match_id", -1).limit(number)

        return pd.DataFrame(list(cur)).drop("_id", axis=1, errors="ignore")

    def get_queues(self, channel_id) -> pd.DataFrame:
        cur_filter = {}
        if channel_id:
            channel_id = int(channel_id)  #mongo db doesn't recognize numpy.Int64 for some reason
            cur_filter["channel_id"] = channel_id

        print(channel_id)
        cur = self.guildDB[self.queues_tbl].find(cur_filter)
        return pd.DataFrame(list(cur)).drop("_id", axis=1, errors="ignore")

    def get_config(self) -> pd.Series:
        row = 0 # one row
        cur_filter = {}
        cur = self.guildDB[self.config_tbl].find()
        df = pd.DataFrame(list(cur)).drop("_id", axis=1, errors="ignore")

        ret = df.loc[row]
        ret["roles_by_elo"] = pd.DataFrame.from_dict(ret["roles_by_elo"], orient="tight")

        return ret



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
        for i in range(len(queue["roles"])):
            queue["roles"][i] = int(queue["roles"][i])

        queuedict = queue.fillna(0).to_dict()

        result = self.guildDB[self.queues_tbl].update_one({"channel_id":queuedict["channel_id"]}, {"$set":queuedict}, upsert=True)
        updated_existing = result.raw_result["updatedExisting"]

    def upsert_config(self, config:pd.Series):

        configdict = config.fillna(0).to_dict()
        configdict["roles_by_elo"] = configdict["roles_by_elo"].to_dict("tight")

        result = self.guildDB[self.config_tbl].update_one({"_":configdict["_"]}, {"$set":configdict}, upsert=True)





    #above: worry about converting numpy to native python

    def add_new_player(self, user_id, **kwargs):

        player = pd.Series()

        player["user_id"] = user_id
        for k in kwargs:
            if k in self.EMPTY_PLAYER.columns:
                player[k] = kwargs[k]
            else:
                raise Exception("Invalid column for player:" + str(k))

        new_player = pd.concat([self.EMPTY_PLAYER, pd.DataFrame(player).T]).fillna(0).iloc[0]
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


        new_queue = pd.concat([self.EMPTY_QUEUE, pd.DataFrame(queue).T]).fillna(0).iloc[0]
        self.upsert_queue(new_queue)

    def add_new_config(self, _=0, **kwargs):
        config = pd.Series()

        config["_"] = _ #currently config has just 1 row so index doesn't matter

        for k in kwargs:
            if k in self.EMPTY_CONFIG.columns:
                config[k] = kwargs[k]
            else:
                raise Exception("Invalid column for config:" + str(k))

        new_config = pd.concat([self.EMPTY_CONFIG, pd.DataFrame(config).T]).fillna(0).iloc[0]

        self.upsert_config(new_config)
