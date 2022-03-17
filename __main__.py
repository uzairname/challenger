import os
from bot import *
from bot import DB
from database import Database
from __init__ import *



if __name__ == "__main__":

    DB.setup(TESTING_GUILD_ID)
    bot = PelaBot(os.environ.get("PELA_TOKEN"))
    bot.run()
    # build_bot(os.environ.get("PELA_TOKEN")).run()