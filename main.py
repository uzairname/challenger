# hi


import os
import pandas as pd
from Challenger.config import Config
import Challenger.database as db
from Challenger.bot import build_bot


if __name__ == "__main__":

    if os.environ.get("ENVIRONMENT") == "development":

        pd.set_option('display.max_columns', None)
        pd.set_option("max_colwidth", 190)
        pd.options.display.width = 100
        pd.options.mode.chained_assignment = None

        testing_DB = db.Session(Config.TESTING_GUILD_ID)
        testing_DB.test()

    build_bot(os.environ.get('DISCORD_TOKEN')).run()