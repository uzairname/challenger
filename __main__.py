import os
from bot import build_bot
import logging
from database import Database

DB = Database()

if __name__ == "__main__":
    DB.setup()
    build_bot(os.environ.get("PELA_TOKEN")).run()


#TODO
# Staff status
# Edit elo after match result updated
# display Leaderboard
# leave queue
# get my recent matches
# get my stats
# join best of 3 or 5 queue with optional option
#
#TODO other notes
# Elo with a small scale factor, and relatively large K value to minimize grinding. approx. 5 games to stabilize elo
# change of less than 1 elo is dispayed as '<1" instead of 0
# displayed elo change is given as rounded. going from 6.7(7) to 5.4(5) is not 6.7-5.4(1), but 7-5(2)