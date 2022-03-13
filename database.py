import time

import psycopg2
import os
import functools
import pandas as pd
import numpy as np
from datetime import datetime


class Database:

    conn = None
    cur = None

    def __init__(self):
        pass

    def open_connection(self):
        self.conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        self.cur = self.conn.cursor()
        print('Database connection opened.')

    def close_connection(self):
        self.cur.close()
        self.conn.commit()
        if self.conn is not None:
            self.conn.close()
            print('Database connection closed.')

    def setup(self):
        self.open_connection()



        # command = """ALTER TABLE players
        # """
        #
        # self.cur.execute(command)



        self.update_match(match_id=36, player1=None)




        # create_player_table(self.conn, self.cur)
        # create_match_table(self.conn, self.cur)

        # print("player elo: ", test_get_elo(conn, cur, "12345"))
        # self.add_player(882323)
        self.update_player(882323, elo=243, time_registered=datetime.fromtimestamp(round(time.time())))


        # self.update_match(match_id=4, player1=111, player2=222, outcome="another outcome!!")
        # self.update_match(match_id=3, elo_change=32)

        # plyr = self.get_players(user_id=1423456)
        # print("plyr: " + str(plyr.empty))
        #
        # plyrs = self.get_players(top_by_elo=3)
        # print(plyr + "\n" + plyrs)

        self.close_connection()


    def create_match(self):
        command = """INSERT INTO matches (player1) VALUES(NULL)"""
        self.cur.execute(command)


    def update_match(self, match_id, **kwargs):

        command = """
            UPDATE matches
            SET"""
        for column in kwargs.keys():
            if not column in self.matches_columns:
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

        print("update_match:\n" + str(command))
        self.cur.execute(command)


    def get_matches(self, player=None, match_id=None, number=1) -> pd.DataFrame:

        command = """SELECT * FROM matches
            WHERE"""
        if match_id:
            command = command + """match_id=""" + str(match_id) + """
            AND """
        if player:
            command = command + """(player1=""" + str(player) + """ or player2=""" + str(player) + """)
            AND"""
        command = command.rsplit("\n", 1)[0]+ """ ORDER BY match_id DESC
            LIMIT """ + str(number) + """"""

        print("█get recent matches: match id:" + str(match_id) + " player: " + str(player) + "\n" + str(command))

        self.cur.execute(command)
        matches = self.cur.fetchall()

        print("matches: " + str(matches))

        command = """SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'matches' """
        self.cur.execute(command)
        columns = []
        for c in self.cur.fetchall():
            columns.append(c[3])  # IDK if this is right!!!

        print(columns)

        return construct_df(columns=columns, rows=matches, index_column="match_id")  # returns a pandas dataframe



    def add_player(self, user_id):
        command = "INSERT INTO players(user_id) VALUES(%s)"
        self.cur.execute(command, (user_id,))


    def update_player(self, player_id, **kwargs):

        command = """
            UPDATE players
            SET"""
        for column in kwargs.keys():
            if not column in self.players_columns:
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

        print("update_player:\n" + str(command))
        self.cur.execute(command)


    def get_players(self, user_id=None, top_by_elo=None):

        command = """
                SELECT * FROM players
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

        print("█get players user id : " + str(user_id) + " top by elo: " + str(top_by_elo) + "\n" + str(command))

        self.cur.execute(command)
        player = self.cur.fetchall()

        player = player

        command = """SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'players' """
        self.cur.execute(command)
        columns = []
        for c in self.cur.fetchall():
            columns.append(c[3])  #IDK if this is right!!!

        columns = columns

        return construct_df(columns=columns, rows=player, index_column="user_id")  #returns a pandas dataframe





    matches_columns = ["match_id", "player1", "player2", "outcome", "p1_declared", "p2_declared", "time_started", "elo_change"]
    def create_match_table(self):
        command = ("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id SERIAL PRIMARY KEY,
            player1 BIGINT,
            player2 BIGINT,
            outcome VARCHAR,
            p1_declared VARCHAR,
            p2_declared VARCHAR
            time_started TIMESTAMP,
            elo_change FLOAT
        )
        """)
        self.cur.execute(command)


    class roles:
        STAFF="staff"
        LILAPELA="lilapela"
    players_columns = ["user_id", "username", "elo", "time_registered", "role"]
    def create_player_table(self):
        command = ("""
            CREATE TABLE IF NOT EXISTS players (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR,
                elo FLOAT,
                role VARCHAR
            )
            """)
        self.cur.execute(command)


def check_errors(func):
    # for database error
    @functools.wraps(func)
    def wrapper_check_errors(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (Exception, psycopg2.DatabaseError) as error:
            print("test add player: " + str(error))

    return wrapper_check_errors


def construct_df(columns, rows, index_column:str):
    #returns pandas dataframe column names and 2d array
    df_data = {}
    for i in range(len(columns)):
        df_data[columns[i]] = []
        for row in rows:
            df_data[columns[i]].append(row[i])

    df = pd.DataFrame(df_data, index=df_data[index_column])
    return df
