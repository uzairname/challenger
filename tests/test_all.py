import unittest

import pandas as pd

from Challenger.config import *
from Challenger.database import *
from Challenger.utils import *

import mongoengine as me



#noinspection PyMethodMayBeStatic
# @unittest.skip("Skipping test_all.py")
class Test_DB(unittest.TestCase):

    # @unittest.skip("Skipping test_all.py")
    def test_get_set_delete_guild(self):

        # Create a guild
        guild = Guild(id=Database.TESTING_GUILD_ID, name="other Test Guild")
        guild.save()

        # Get the guild
        guild = Guild.objects(guild_id=Database.TESTING_GUILD_ID).first()

        # Check the name
        self.assertEqual(guild.name, "other Test Guild")

        # Set the staff role
        guild.staff_role_id = 94833278723897239

        # Check the staff role
        self.assertEqual(guild.staff_role_id, 94833278723897239)
        guild_ = Guild.objects(guild_id=Database.TESTING_GUILD_ID).first()
        self.assertEqual(guild_.staff_role_id, None)
        guild.save()
        self.assertEqual(guild.staff_role_id, 94833278723897239)



        self.assertEqual(guild.admin_role_id, None)

        # Delete the guild
        guild.delete()

        # Check the guild
        guild = Guild.objects(guild_id=Database.TESTING_GUILD_ID).first()
        self.assertEqual(guild, None)



    # @unittest.skip("Skipping test_all.py")
    def test_leaderboards_players_lobbies(self):


        # Create a guild if it doesn't exist
        guild = Guild.objects(guild_id=Database.TESTING_GUILD_ID).first()

        if guild is None:
            guild = Guild(guild_id=Database.TESTING_GUILD_ID, name="Test Guild")

        self.assertEqual([lb for lb in guild.leaderboards], [])

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
        player = Player.objects(user_id=test_user_id, leaderboard_name=lb_names[1], guild_id=Database.TESTING_GUILD_ID).first()
        # add a player to the leaderboard if not already in it. Player chooses the leaderboard by name
        if player is None:
            player = Player(user_id=test_user_id, leaderboard_name=lb_names[1], guild_id=Database.TESTING_GUILD_ID, username="Test User#1234")
            player.save()


        # a player joins the lobby in channel 2
        guild.leaderboards.filter(name=lb_names[1]).first().lobbies.filter(channel_id=1).first().player_in_q = player

        guild.save()

        self.assertEqual(Guild.objects(guild_id=Database.TESTING_GUILD_ID).first().leaderboards.filter(name=lb_names[1]).first().lobbies.filter(channel_id=1).first().player_in_q.fetch().username, "Test User#1234")

        #remove the player from the lobby
        guild = Guild.objects.filter(guild_id=Database.TESTING_GUILD_ID).first()
        guild.leaderboards.filter(name=lb_names[1]).first().lobbies.filter(channel_id=1).first().player_in_q = None

        guild.save()

        # check the player in queue
        self.assertEqual(Guild.objects(guild_id=Database.TESTING_GUILD_ID).first().leaderboards.filter(name=lb_names[1]).first().lobbies.filter(channel_id=1).first().player_in_q, None)


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


def matches_migration():
    DB = Guild_DB(Database.DEV_GUILD_ID)

    matches = DB.get_matches()

    matches.to_csv("test_matches.csv")

    #connect to the development database and put all the matches in from this csv

    db_name = "development"
    mongodb_url_with_database = os.environ.get("MONGODB_URL").replace("mongodb.net/?", "mongodb.net/" + db_name + "?")

    connection = me.connect(host=mongodb_url_with_database)

    connection.get_database().drop_collection("matches")
    connection.get_database().drop_collection("players")

    matches = pd.read_csv("test_matches.csv")
    os.remove("test_matches.csv")

    leaderboard_name = "Ast"
    guild_id = Database.DEV_GUILD_ID

    for i, match in matches.iterrows():
        print(match.name)
        outcome = match["outcome"]
        if not match["outcome"] in [Outcome.CANCELLED, Outcome.PLAYER_1, Outcome.PLAYER_2, Outcome.DRAW]:
            outcome = Outcome.CANCELLED

        print(match["p1_id"], "\n", DB.get_players(user_id=match["p1_id"]))

        player1 = Player(user_id=match["p1_id"], leaderboard_name=leaderboard_name, guild_id=guild_id, username=DB.get_players(user_id=match["p1_id"]).iloc[0]["username"])

        player2 = Player(user_id=match["p2_id"], leaderboard_name=leaderboard_name, guild_id=guild_id, username=DB.get_players(user_id=match["p2_id"]).iloc[0]["username"])
        try:
            player1.save()
        except me.NotUniqueError:
            player1 = Player.objects(user_id=match["p1_id"], leaderboard_name=leaderboard_name, guild_id=guild_id).first()
            pass
        try:
            player2.save()
        except me.NotUniqueError:
            player2 = Player.objects(user_id=match["p2_id"], leaderboard_name=leaderboard_name, guild_id=guild_id).first()
            pass

        match = Match(leaderboard_name=leaderboard_name, guild_id=guild_id, match_id=match["match_id"],
                      outcome=outcome,
                      time_started=match["time_started"],

                      player1=player1, player2=player2,
                      player1_elo=match["p1_elo"], player2_elo=match["p2_elo"],
                      player1_RD=350, player2_RD=350,
                      )
        match.save()

    me.disconnect_all()

if __name__ == "__main__":

    me.disconnect_all()

    matches_migration()

    testing_db_name = "testing"

    mongodb_url_with_database = os.environ.get("MONGODB_URL").replace("mongodb.net/?", "mongodb.net/" + testing_db_name + "?")

    connection = me.connect(host=mongodb_url_with_database)

    dev_database = connection.get_database(testing_db_name)
    collections = dev_database.list_collection_names()
    for collection in collections:
        dev_database.drop_collection(collection)

    unittest.main()



