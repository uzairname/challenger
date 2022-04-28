import unittest

import pandas as pd

from Challenger.config import *
from Challenger.database import *
from Challenger.helpers import *

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

    @unittest.skip("Skipping test_all.py")
    def test_get_set_delete_guild(self):

        # Create a guild
        guild = Guild(id=Database_Config.TESTING_GUILD_ID, name="Test Guild")
        guild.save()

        # Get the guild
        guild = Guild.objects(guild_id=Database_Config.TESTING_GUILD_ID).first()

        # Check the name
        self.assertEqual(guild.name, "Test Guild")

        # Set the staff role
        guild.staff_role_id = 94833278723897239

        # Check the staff role
        self.assertEqual(guild.staff_role_id, 94833278723897239)
        guild_ = Guild.objects(guild_id=Database_Config.TESTING_GUILD_ID).first()
        self.assertEqual(guild_.staff_role_id, None)
        guild.save()
        self.assertEqual(guild.staff_role_id, 94833278723897239)



        self.assertEqual(guild.admin_role_id, None)

        # Delete the guild
        guild.delete()

        # Check the guild
        guild = Guild.objects(guild_id=Database_Config.TESTING_GUILD_ID).first()
        self.assertEqual(guild, None)



    # @unittest.skip("Skipping test_all.py")
    def test_leaderboards_players_lobbies(self):


        # Create a guild if it doesn't exist
        guild = Guild.objects(guild_id=Database_Config.TESTING_GUILD_ID).first()

        if guild is None:
            guild = Guild(id=Database_Config.TESTING_GUILD_ID, name="Test Guild")

        self.assertEqual([lb.leaderboard for lb in guild.leaderboards], [])

        # if the guild has no leaderboards create a leaderboard and add it to the guild
        if not guild.leaderboards:
            guild.leaderboards.append(Leaderboard(name="Test Guild Default Lb"))

        self.assertEqual(guild.leaderboards[0].name, "Test Guild Default Lb")

        # add another lb to the guild
        guild.leaderboards.append(Leaderboard(name="Test Guild Second Lb"))

        lb_names = [lb.name for lb in guild.leaderboards]
        self.assertEqual(lb_names, ["Test Guild Default Lb", "Test Guild Second Lb"])


        # Add a lobby to both the leaderboards. user chooses the loaderboard by name

        # make a lobby with the lb
        new_lobby = Lobby(channel_id=1, name="test lobby 2nd lb")
        guild.leaderboards.filter(name=lb_names[1]).first().lobbies.append(new_lobby)



        # player registeres for lb 2. find or add a user, then add a player
        test_user_id = 24899
        user = User.objects(user_id=test_user_id).first()
        if user is None:
            user = User(user_id=test_user_id, username="Test User#1234")

        # add a player to the leaderboard if not already in it. Player chooses the leaderboard by name
        player = guild.leaderboards.filter(name=lb_names[0]).first().players.filter(user=test_user_id).first()
        if not player:
            player = Player(user=user)
            guild.leaderboards.filter(name=lb_names[0]).first().players.append(player)


        # a player joins the lobby in channel 2
        guild.leaderboards.filter(name=lb_names[1]).first().lobbies.filter(channel_id=1).first().user_in_q = user

        guild.save()
        user.save()



        guild = Guild.objects(guild_id=45).first()
        if not guild:
            guild = Guild(guild_id=45)

        leaderboard = guild.leaderboards.filter(name="Ast").first()

        if leaderboard:
            leaderboard.name = "Ast"
        else:
            leaderboard = Leaderboard(name="Ast")
            guild.leaderboards.append(leaderboard)

        guild.save()





if __name__ == "__main__":

    connection = me.connect(host=Database_Config.mongodb_url_with_database)

    dev_database = connection.get_database("testing")
    collections = dev_database.list_collection_names()
    for collection in collections:
        dev_database.drop_collection(collection)

    unittest.main()