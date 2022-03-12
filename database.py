import psycopg2
import os
import functools
import pandas as pd
import numpy as np

# helper functions to do stuff
# TODO make this

#table of matches:
#columns: Match id, players(list of ids), result

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

        # command = """ALTER TABLE matches
        #     ADD declared_by VARCHAR,
        #     ADD time_started TIMESTAMP
        # """

        # self.cur.execute(command)

        # create_player_table(self.conn, self.cur)
        # create_match_table(self.conn, self.cur)

        # print("player elo: ", test_get_elo(conn, cur, "12345"))
        # test_add_player(self.conn, self.cur, "12345678", "feap", "100")

        self.update_match(match_id=4, player1=111, player2=222, outcome="another outcome!!")
        self.update_match(match_id=3, elo_change=32)



        try:
            a = self.get_recent_matches(player=4619427).loc[0, :]
            print("a:  " + str(a))
        except :
            print("█error")
    #Functions below:

    def create_match(self):
        command = """INSERT INTO matches (player1) VALUES(NULL)"""
        self.cur.execute(command)


    def update_match(self, match_id, player1=None, player2=None, outcome=None, declared_by=None, elo_change=None):

        def if_notnull(x, string):
            if not x is None:
                return string
            else:
                return """"""

        command = """
            UPDATE matches
            SET"""\
                  + if_notnull(player1, """
            player1 = """ + str(player1) + """,""") \
            \
                  + if_notnull(player2, """
            player2 = """ + str(player2) + """,""") \
            \
                  + if_notnull(outcome, """
            outcome = '""" + str(outcome) + """',""") \
            \
                  + if_notnull(declared_by, """
            declared_by = '""" + str(declared_by) + """',""") \
            \
                  + if_notnull(elo_change, """
            elo_change = """ + str(elo_change) + """,""")

        command = command[:-1] + """
            WHERE match_id = """ + str(match_id) + """
        """

        self.cur.execute(command)

    def get_elo_by_player(self, user_id):
        command = "SELECT elo FROM players WHERE user_id=%s;"
        self.cur.execute(command, (user_id,))
        return self.cur.fetchall()

    def is_player_registered(self, user_id) -> bool:
        raise NotImplementedError


    def get_recent_matches(self, player=None, number=1) -> pd.DataFrame:
        if player is not None:
            command = """
                SELECT * FROM matches
                WHERE player1=""" + str(player) + """ or player2=""" + str(player) + """
                ORDER BY match_id DESC
                LIMIT """ + str(number) + """
            """
        else:
            command = """ SELECT * FROM matches ORDER BY match_id DESC LIMIT """ + str(number)

        self.cur.execute(command)
        matches = self.cur.fetchall()

        print("matches: " + str(matches))

        command = """SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'matches' """
        self.cur.execute(command)
        columns = []
        for c in self.cur.fetchall():
            columns.append(c[3])  #IDK if this is right!!!

        return construct_df(columns=columns, rows=matches, index_column="match_id")  #returns a pandas dataframe



    def add_player(self, new_user_id, new_username, new_elo):
        command = "INSERT INTO players(user_id, username, elo) VALUES(%s, %s, %s)"
        self.cur.execute(command, (new_user_id, new_username, new_elo,))


    def add_player_to_queue(self, user_id) -> int: #returns new match id
        raise NotImplementedError


    def create_match_table(self):
        command = ("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id SERIAL PRIMARY KEY,
            time_started TIMESTAMP,
            player1 BIGINT,
            player2 BIGINT,
            outcome VARCHAR,
            declared_by VARCHAR,
            elo_change FLOAT
        )
        """)
        self.cur.execute(command)

    def create_player_table(self):
        command = ("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INT PRIMARY KEY,
                username VARCHAR,
                elo VARCHAR
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

    df_data = {}
    for i in range(len(columns)):
        df_data[columns[i]] = []
        for row in rows:
            df_data[columns[i]].append(row[i])

    df = pd.DataFrame(df_data, index=df_data[index_column])
    return df
