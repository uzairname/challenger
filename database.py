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

    create_player_table(conn, cur)
    create_match_table(conn, cur)

    print("player elo: ", test_get_elo(conn, cur, "12345"))
    test_add_player(conn, cur, "12345678", "feap", "100")

    # close connections
    cur.close()
    conn.commit()
    if conn is not None:
        conn.close()
        print('Database connection closed.')


@check_errors
def test_add_player(conn, cur, new_user_id, new_username, new_elo):
    sql = "INSERT INTO players(user_id, username, elo) VALUES(%s, %s, %s)"
    cur.execute(sql, (new_user_id, new_username, new_elo,))


@check_errors
def test_get_elo(conn, cur, player_id):
    sql = f"SELECT elo FROM players WHERE user_id=%s;"

    cur.execute(sql, (player_id,))

    return cur.fetchall()


@check_errors
def create_match_table(conn, cur):
    command = ("""
    CREATE TABLE IF NOT EXISTS players (
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
