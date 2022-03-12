import os
from bot import build_bot
import logging
from database import Database

DB = Database()

if __name__ == "__main__":
    DB.create_connection()
    DB.setup()
    DB.close_connection()
    build_bot(os.environ.get("PELA_TOKEN")).run()