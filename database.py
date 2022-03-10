import psycopg2
import os
import functools


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


@check_errors
def config_database():
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cur = conn.cursor()

    create_player_table(conn, cur)

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


def create_player_table(conn, cur):
    command = ("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INT PRIMARY KEY,
            username VARCHAR,
            elo VARCHAR
        )
        """)
    cur.execute(command)
