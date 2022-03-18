from __init__ import *

import psycopg2
import os
from sqlalchemy import create_engine
import functools
import pandas as pd
from plugins.utils import *


def check_errors(func):
    # for database error
    @functools.wraps(func)
    def wrapper_check_errors(*args, **kwargs):
        # try:
        return func(*args, **kwargs)
        # except (Exception, psycopg2.DatabaseError) as error:
        #     print("error in " + str(func) + ": " + str(error))

    return wrapper_check_errors


class Database:

    # conn = None
    # cur = None
    # guild_id = None #should be set every time connection is opened
    # players_tbl = None
    # matches_tbl = None
    # queues_tbl = None #why does it give error 'Database' object has no attribute 'queues_tbl' if this line is queues_tbl:str ?
    # config_tbl = None

    def __init__(self):
        pass

    def setup(self, guild_id): #setup is always called at the start, and can be called in guildstartingevent, to update DBs for every server
        self.open_connection(guild_id)

        self.reset_queues_table()
        q_df = self.get_queues()
        #
        # command = """
        # DROP TABLE queues_0
        # """
        # self.cur.execute(command)

        new_q = construct_df([[2, 345, [234]]], ["queue_id", "channels", "roles"])

        new_q_df = replace_col_or_concat(q_df, new_q, "queue_id")

        self.update_queues_df(new_q_df)

        self.close_connection()


    #matches =========================================================

    def create_match(self):
        command = """INSERT INTO """ + self.matches_tbl + """ DEFAULT VALUES"""
        self.cur.execute(command)

    def update_match(self, match_id, **kwargs):

        command = """
            UPDATE """ + self.matches_tbl + """ 
            SET"""
        for column in kwargs.keys():
            if not column in self.get_columns(self.matches_tbl):    #TODO fix this
                print("column not found: " + str(column))
                continue
            command = command + """
            """ + str(column) + """ = """

            if kwargs[column]:
                val = """'""" + str(kwargs[column]) + """'"""
            else:
                val = "NULL"
            command = command + val + ""","""

        command = command[:-1] + """
            WHERE match_id = """ + str(match_id) + """
        """

        print("█UPDATE MATCH for guild " + str(self.guild_id) + ": " + str(match_id) + "kwargs: " + str(kwargs)  +"\n")
        self.cur.execute(command)


    def get_recent_matches(self, player=None, match_id=None, number=1) -> pd.DataFrame: #TODO implement isfull

        command = """SELECT * FROM """ + self.matches_tbl + """ 
            WHERE"""
        if match_id:
            command = command + """ match_id=""" + str(match_id) + """
            AND"""
        if player:
            command = command + """ (player1=""" + str(player) + """ or player2=""" + str(player) + """)
            AND"""
        command = command.rsplit("\n", 1)[0]+ """ ORDER BY match_id DESC
            LIMIT """ + str(number) + """"""

        print("█GET MATCHES from guild: " + str(self.guild_id) + ": by player: " + str(player) + ", id: " + str(match_id) + ", number: " + str(number) + "\n")

        self.cur.execute(command)
        matches = self.cur.fetchall()

        command = """SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '""" + self.matches_tbl + """' """
        self.cur.execute(command)
        columns = []
        for c in self.cur.fetchall():
            columns.append(c[3])  # IDK if this is right!!!

        df = construct_df(columns=columns, rows=matches, index_column="match_id").fillna(0)

        return df  # returns a pandas dataframe


    #players =========================================================

    def add_player(self, user_id):
        command = """INSERT INTO """ + self.players_tbl + """ (user_id) VALUES(%s)"""
        self.cur.execute(command, (user_id,))


    def update_player(self, player_id, **kwargs):

        command = """
            UPDATE """ + self.players_tbl + """
            SET"""

        for column in kwargs.keys():
            if not column in self.get_columns(self.players_tbl):   #TODO check this
                print("Column not found: " + str(column))
                continue
            command = command + """
            """ + str(column) + """ = """

            if kwargs[column]:
                val = """'""" + str(kwargs[column]) + """'"""
            else:
                val = "NULL"
            command = command + val + ""","""

        command = command[:-1] + """
            WHERE user_id = """ + str(player_id) + """
        """

        print("█UPDATE " + self.players_tbl + ": " + str(player_id) + ", kwargs: " + str(kwargs) + "\n")
        self.cur.execute(command)


    def get_players(self, user_id=None, top_by_elo=None):

        command = """
                SELECT * FROM """ + self.players_tbl + """
            """
        if user_id:
            command = command + """
                WHERE user_id=""" + str(user_id) + """
            """
        elif top_by_elo:
            command = command + """
                ORDER BY elo DESC
                LIMIT """ + str(top_by_elo) + """
            """

        print("█GET PLAYER: " + str(user_id) + " top by elo: " + str(top_by_elo) + "\n")

        self.cur.execute(command)
        player = self.cur.fetchall()
        columns = self.get_columns(self.players_tbl)

        df = construct_df(columns=columns, rows=player, index_column="user_id").fillna(0)

        return df  #returns a pandas dataframe




    # queues =========================================================

    def update_queues_df(self, df):
        postgresURL = os.environ.get("DATABASE_URL").replace("postgres://", "postgresql://", 1)
        self.engine = create_engine(postgresURL)

        self.close_connection()

        print("q df: \n"+ str(df) + "\nindex: " + str(df.index))

        df.to_sql(self.queues_tbl, self.engine, if_exists="replace", index=False)

        self.open_connection(self.guild_id)

    def get_queues_df(self):
        pass


    def remove_queue(self, queue_id):
        pass

    def update_queue(self, queue_id, **kwargs):
        command = """
            UPDATE """ + self.queues_tbl + """
            SET"""

        for column in kwargs.keys():
            if not column in self.get_columns(self.queues_tbl):
                print("Column not found: " + str(column))
                continue
            command = command + """
            """ + str(column) + """ = """

            if kwargs[column]:
                val = """'""" + str(kwargs[column]) + """'"""
            else:
                val = "NULL"
            command = command + val + ""","""

        command = command[:-1] + """
            WHERE queue_id = """ + str(queue_id) + """
        """

        print("█UPDATE " + self.queues_tbl + ": " + str(queue_id) + ", kwargs: " + str(kwargs) + "\n" + str(command))
        self.cur.execute(command)


    def get_queues(self):

        # Each Channel can only have 1 queue, each queue can have multiple channels
        command = """
            SELECT * FROM """ + self.queues_tbl + """
        """

        self.cur.execute(command)

        queues = self.cur.fetchall()
        columns = self.get_columns(self.queues_tbl)

        df = construct_df(columns=columns, rows=queues, index_column="queue_id")
        df[["player1","player2"]] = df[["player1","player2"]].astype("Int64").fillna(0)

        return df



    #Below: non- guild specific
    def get_config(self):

        postgresURL = os.environ.get("DATABASE_URL").replace("postgres://", "postgresql://", 1)
        self.engine = create_engine(postgresURL)

        sql = """
            SELECT * FROM """ + self.config_tbl + """
        """

        df = pd.read_sql(sql, self.engine)

        return df

    #below: non guild specific


    def update_config_table(self, **kwargs):
        self.close_connection()
        postgresURL = os.environ.get("DATABASE_URL").replace("postgres://", "postgresql://", 1)
        self.engine = create_engine(postgresURL)

        old_config_df = self.get_config()

        cols = ["guild_id"]

        new_row = construct_df([[self.guild_id]], cols)
        print("████\n" + str(new_row))

        new_config_df = replace_col_or_concat(old_config_df, new_row, "guild_id")

        new_config_df.to_sql(self.config_tbl, self.engine, if_exists='replace', index=False)

        self.open_connection(self.guild_id)








    #===================================

    def get_columns(self, table_name):
        command = """SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '""" + table_name + """'"""
        self.cur.execute(command)
        columns = []
        for c in self.cur.fetchall():
            columns.append(c[3])  # this is not

        return columns



    @check_errors
    def reset_players_table(self):

        table_name = self.players_tbl

        command = """
        DROP TABLE IF EXISTS """ + table_name + """;
        CREATE TABLE IF NOT EXISTS """ + table_name + """ (
            user_id BIGINT PRIMARY KEY,
            username VARCHAR,
            time_registered TIMESTAMP,
            elo FLOAT,
            role VARCHAR
        )
        """
        self.cur.execute(command)

        print("███ RESET Table " + table_name)

    #below: reset tables. Any code changes here won't show up in the server until they reset their tables
    @check_errors
    def reset_matches_table(self):

        table_name = self.matches_tbl

        command = """
        DROP TABLE IF EXISTS """ + table_name + """;
        CREATE TABLE IF NOT EXISTS """ + table_name + """ (
            match_id SERIAL PRIMARY KEY,
            time_started TIMESTAMP,
            player1 BIGINT,
            player2 BIGINT,
            p1_declared VARCHAR,
            p2_declared VARCHAR,
            p1_elo FLOAT,
            p2_elo FLOAT,
            outcome VARCHAR
        )
        """
        self.cur.execute(command)

        print("███ RESET Table " + table_name)


    @check_errors
    def reset_queues_table(self):

        table_name = self.queues_tbl

        command = """
        DROP TABLE IF EXISTS """ + table_name + """;
        CREATE TABLE IF NOT EXISTS """ + table_name + """ (
            queue_id SERIAL PRIMARY KEY,
            queue_name VARCHAR,
            player1 BIGINT,
            player2 BIGINT,
            channels BIGINT[],
            roles BIGINT[]
        )
        """
        self.cur.execute(command)

        print("███ RESET Table " + table_name)



    @check_errors
    def reset_config_table(self):
        table_name = "config"

        command = """
        DROP TABLE IF EXISTS """ + table_name + """;
        CREATE TABLE IF NOT EXISTS """ + table_name + """ (
            guild_id BIGINT PRIMARY KEY,
            staff_roles BIGINT[],
            banned_players BIGINT[],
            results_channel BIGINT
        )
        """

        self.cur.execute(command)

        print("███ RESET config table " + table_name)



    def open_connection(self, guild_id):
        self.guild_id = guild_id

        if guild_id==TESTING_GUILD_ID: #special case for pela server
            self.guild_id = 0

        self.players_tbl = "players_" + str(self.guild_id)
        self.matches_tbl = "matches_" + str(self.guild_id)
        self.queues_tbl = "queues_" + str(self.guild_id)
        self.config_tbl = "config"

        self.conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        self.cur = self.conn.cursor()

        print('Database connection opened')

    def close_connection(self):
        self.cur.close()
        self.conn.commit()
        if self.conn is not None:
            self.conn.close()
            print('Database connection closed')

