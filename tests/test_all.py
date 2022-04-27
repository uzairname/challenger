import unittest

import pandas as pd

from Challenger.config import *
from Challenger.database import *
from Challenger.utils import *

import mongoengine as me

@unittest.skip("Skipping test_all.py")
class Test_Bayeselo(unittest.TestCase):

    def test_bayeselo(self):

        results = [(1200, "win"), (1250, "loss"), (1350, "win"), (1300, "loss")]

        calc_bayeselo(results)

        self.assertEqual(True, True)



#noinspection PyMethodMayBeStatic
# @unittest.skip("Skipping test_all.py")
class Test_DB(unittest.TestCase):


    def test_get_set_delete_guild(self):

        # Create a guild
        database.add_guild(DB.TESTING_GUILD_ID, name="Test Guild")

        # Get the guild
        guild = Guild.objects(guild_id=DB.TESTING_GUILD_ID).first()

        # Check the name
        self.assertEqual(guild.name, "Test Guild")

        # Set the staff role
        guild.set_staff_role(94833278723897239)

        # Check the staff role
        self.assertEqual(guild.staff_role_id, 94833278723897239)

        guild = Guild.objects(guild_id=DB.TESTING_GUILD_ID).first()
        self.assertEqual(guild.staff_role_id, 94833278723897239)

        self.assertEqual(guild.admin_role_id, None)

        # Delete the guild
        guild.delete()

        # Check the guild
        guild = Guild.objects(guild_id=DB.TESTING_GUILD_ID).first()
        self.assertEqual(guild, None)

        print("get set test guild")


    def test_leaderboards_players_lobbies(self):

        # Create a guild
        guild = Guild(id=DB.TESTING_GUILD_ID, name="Test Guild")

        self.assertEqual([lb.leaderboard for lb in guild.guild_leaderboards], [])

        # Create a leaderboard
        id = bson.ObjectId()
        leaderboard = Leaderboard(lb_id=id, name="Test Guild Default Lb")
        leaderboard.save()

        # Create a guild leaderboard
        guild_leaderboard = Guild_Leaderboard(leaderboard=leaderboard, name=leaderboard.name)

        # Add it to the guild
        guild.guild_leaderboards.append(guild_leaderboard)

        self.assertEqual(guild.guild_leaderboards[0].leaderboard.fetch().name, "Test Guild Default Lb")


        main_lobby = Lobby1v1()
        guild.get_guild_lb_by_name("Test Guild Default Lb").lobbies.append(main_lobby)

        # Create a user
        database.add_user(user_id=23423094823234, username="Test User#1234")

        # add the user to the guild's default leaderboard
        guild.get_guild_lb_by_name("Test Guild Default Lb").leaderboard.fetch().players.append(Player(user=User.objects(user_id=23423094823234).first()))

        self.assertEqual(guild.get_guild_lb_by_name("Test Guild Default Lb").leaderboard.fetch().players[0].user.fetch().username, "Test User#1234")









class test_(unittest.TestCase):

    def test_(self):
        database.add_guild(DB.TESTING_GUILD_ID, name="Test Guild")




if __name__ == "__main__":

    connection = me.connect(host=DB.mongodb_url_with_database)

    dev_database = connection.get_database("development")
    collections = dev_database.list_collection_names()
    for collection in collections:
        dev_database.drop_collection(collection)

    unittest.main()