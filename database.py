import psycopg2
import os
import functools


# helper functions to do stuff
# TODO make this

#table of matches:
#columns: Match id, players(list of ids), result


def is_player_registered(user_id) -> bool:
    raise NotImplementedError


def get_elo_by_player(user_id):
    raise NotImplementedError


def get_matches_by_player(user_id, number):
    # returns most recent matches played by player
    raise NotImplementedError



def add_player(user_id, username, elo) -> None:
    raise NotImplementedError


def add_player_to_queue(user_id) -> int: #returns new match id
    #if latest match has 2 players, creates new match with 1 player, or adds to latest match
    #returns error if player already in queue
    raise NotImplementedError

def remove_player_from_queue(user_id):
    raise NotImplementedError

def create_match(player_ids, time) -> int: #returns new match id
    raise NotImplementedError


def edit_match(match_id, result) -> None:
    #update the match results
    raise NotImplementedError




# postgres database functions

def check_errors(func):
    # for database error
    @functools.wraps(func)
    def wrapper_check_errors(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (Exception, psycopg2.DatabaseError) as error:
            print("test add player: " + str(error))

    return wrapper_check_errors



def config_database():
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cur = conn.cursor()

    """ALTER TABLE matches 
    ALTER COLUMN player1 SET DATA TYPE
    ALTER COLUMN player2 SET DATA TYPE 
    """

    # create_player_table(conn, cur)
    # create_match_table(conn, cur)

    # print("player elo: ", test_get_elo(conn, cur, "12345"))
    # test_add_player(conn, cur, "12345678", "feap", "100")


    test_update_match(conn, cur, match_id=3, player1=111, player2=222, outcome="NEW OUTCOME")

    test_update_match(conn, cur, match_id=3, elo_change=32)


    # close connections
    cur.close()
    conn.commit()
    if conn is not None:
        conn.close()
        print('Database connection closed.')


@check_errors
def test_add_player(conn, cur, new_user_id, new_username, new_elo):
    command = "INSERT INTO players(user_id, username, elo) VALUES(%s, %s, %s)"
    cur.execute(command, (new_user_id, new_username, new_elo,))


@check_errors
def test_get_elo(conn, cur, player_id):
    command = f"SELECT elo FROM players WHERE user_id=%s;"

    cur.execute(command, (player_id,))

    return cur.fetchall()

def test_create_match(conn, cur, player1=None, player2=None, outcome=None, elo_change=None):
    command = """INSERT INTO matches (player1, player2, outcome, elo_change) VALUES(%s, %s, %s, %s)"""
    cur.execute(command, (player1, player2, outcome, elo_change))


def test_update_match(conn, cur, match_id, player1=None, player2=None, outcome=None, elo_change=None):

    def if_notnull(x, string):
        if not x is None:
            return string
        else:
            return """"""

    command = """
        UPDATE matches
        SET"""\
        + if_notnull(player1, """
        player1 = """ + str(player1) + """""")\
        + if_notnull(player2, """,
        player2 = """ + str(player2) + """""")\
        + if_notnull(outcome, """,
        outcome = '""" + str(outcome) + """'""")\
        + if_notnull(elo_change, """
        elo_change = """ + str(elo_change) + """""")\
        + """
        WHERE match_id = """ + str(match_id) + """
    """
    print(command)


    # command = """
    #     UPDATE matches
    #     SET player1 = '""" + str(player1) + """'
    #     SET player2 = '""" + str(player2) + """'
    #     SET outcome = '""" + outcome + """'
    #     SET elo_change = '""" + elo_change + """'
    #     WHERE match_id = '""" + match_id + """'
    #     """

    cur.execute(command)

def create_match_table(conn, cur):
    command = ("""
    CREATE TABLE IF NOT EXISTS matches (
        match_id SERIAL PRIMARY KEY,
        player1 INT,
        player2 INT,
        outcome VARCHAR,
        elo_change NUMERIC
    )
    """)
    cur.execute(command)


def create_player_table(conn, cur):
    command = ("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INT PRIMARY KEY,
            username VARCHAR,
            elo VARCHAR
        )
        """)
    cur.execute(command)
