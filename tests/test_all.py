import unittest

import pandas as pd

from Challenger.config import Database_Config
from Challenger.database import Session

from datetime import datetime, timedelta



class Test(unittest.TestCase):

    def test_test(self):
        DB = Session(Database_Config.TEST_GUILD_ID)
        DB.delete_database()
        DB.create_collections()

        DB.test()


#noinspection PyMethodMayBeStatic
@unittest.skip("Skipping")
class Test_DB(unittest.TestCase):

    def setup_db(self):
        DB = Session(Database_Config.TEST_GUILD_ID)
        DB.delete_database()
        DB.create_collections()

    def test_matches(self):

        """
        Adds a new match and gets it back. checks if the match is the same
        """

        DB = Session(Database_Config.TEST_GUILD_ID)
        DB.delete_all_matches()

        match = DB.get_new_match()
        match["p1_id"] = 48736582983653827
        match["p2_id"] = 34365829836532398

        DB.upsert_match(match)
        match2 = DB.get_matches(limit=1).iloc[0]

        assert match.equals(match2)


    def test_get_matches(self):

        DB = Session(Database_Config.TEST_GUILD_ID)
        DB.delete_all_matches()
        assert DB.get_matches().equals(DB.empty_match_df)

        for i in range(20):
            match = DB.get_new_match()
            match["p1_id"] = i%2
            DB.upsert_match(match)

        #ensure that filters are applied in this order: increasing, then offset, then number
        matches = DB.get_matches(user_id=0, limit=5, increasing=False, skip=1) #the 5 matches before the second to last one

        print("matches: \n" + str(matches))

        expected_index = pd.Index([17, 15, 13, 11, 9])
        assert matches.index.equals(expected_index)


    # unittest.main()



if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option("max_colwidth", 90)
    pd.options.display.width = 100
    pd.options.mode.chained_assignment = None
    unittest.main()