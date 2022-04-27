import unittest

import pandas as pd

from Challenger.config import *
from Challenger.database import *
from Challenger.utils import *

import mongoengine as me


class Test_Bayeselo(unittest.TestCase):

    def test_bayeselo(self):

        results = [(1200, "win"), (1250, "loss"), (1350, "win"), (1300, "loss")]

        calc_bayeselo(results)

        self.assertEqual(True, True)



#noinspection PyMethodMayBeStatic
class Test_DB(unittest.TestCase):

    def test_get_set_delete_guild(self):

        # Create a guild
        database.add_guild(DB.TESTING_GUILD_ID, name="Test Guild")

        # Get the guild
        guild = database.get_guild(DB.TESTING_GUILD_ID)

        # Check the name
        self.assertEqual(guild.name, "Test Guild")

        # Set the staff role
        guild.set_staff_role(94833278723897239)

        # Check the staff role
        self.assertEqual(guild.staff_role_id, 94833278723897239)

        guild = database.get_guild(DB.TESTING_GUILD_ID)
        self.assertEqual(guild.staff_role_id, 94833278723897239)

        # Delete the guild
        guild.delete()

        # Check the guild
        guild = database.get_guild(DB.TESTING_GUILD_ID)
        self.assertEqual(guild, None)

        print("get set test guild")



if __name__ == "__main__":

    print(os.environ.get("MONGODB_URL").replace("mongodb.net/?", "mongodb.net/" + os.environ.get("ENVIRONMENT") + "?"))

    me.connect(host=DB.mongodb_url_with_database)

    unittest.main()