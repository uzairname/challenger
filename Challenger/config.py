import os
from typing import final
from hikari import Permissions


@final
class App:

    VERSION = '1.0.0 dev5'

    GITHUB_LINK = "https://github.com/lilapela/competition"
    DISCORD_SERVER_INVITE = "https://discord.gg/bunZ3gadBU"
    TOP_GG_LINK = "https://top.gg/bot/908432840566374450"
    OWNER_ID = 623257053879861248  # Lilapela's ID
    DEV_GUILD_ID = 907729885726933043 # Testing discord server

    OWNER_AVATAR = "https://cdn.discordapp.com/avatars/623257053879861248/18473bb00ae3869688ab15c9a41da270.png"

    REQUIRED_PERMISSIONS = Permissions.VIEW_CHANNEL | Permissions.SEND_MESSAGES | Permissions.EMBED_LINKS | Permissions.MANAGE_ROLES
    PERMS_ERR_MSG = f"The bot is missing some required permissions either for this channel or the server"
    if os.environ.get("ENVIRONMENT") == "development":
        INVITE_LINK = "https://discord.com/api/oauth2/authorize?client_id=951132825803964447&permissions=" + str(REQUIRED_PERMISSIONS.value) + "&scope=bot%20applications.commands"
    elif os.environ.get("ENVIRONMENT") == "production":
        INVITE_LINK =  "https://discord.com/api/oauth2/authorize?client_id=908432840566374450&permissions=" + str(REQUIRED_PERMISSIONS.value) + "&scope=bot%20applications.commands"

    COMPONENT_TIMEOUT = 1200
    QUEUE_JOIN_TIMEOUT = 600


class Elo:

    STARTING_ELO = 1000
    # Everyone's starting elo, also everyone's average elo

    STARTING_RD = 350
    # Everyone's starting rating deviation

    SCALE = 400
    # The elo difference which represents a 10x difference in skill. Used in elo calculation.

    K_COEF = 0.1 #learning rate for the stochastic gradient descent
    K = SCALE * K_COEF
    # Maximum change in one game

    NUM_PLACEMENT_MATCHES = 3  # How many of the first games are scored by provisional elo


@final
class Database_Config:

    mongodb_client = None

    mongodb_url_with_database = os.environ.get("MONGODB_URL").replace("mongodb.net/?", "mongodb.net/" + os.environ.get("ENVIRONMENT") + "?")

    B2T_GUILD_ID =     921447683154145331
    TESTING_GUILD_ID = 999999999999999999

    # database names for some known discord servers, for ease of use. "testing" is for unit testing
    KNOWN_GUILDS = {1: "testing", App.DEV_GUILD_ID: "development", 947184983120957452: "PX", B2T_GUILD_ID: "B2T"}



import pandas as pd

def set_pandas_display_options():

    pd.set_option('display.max_columns', None)
    pd.set_option("max_colwidth", 90)
    pd.options.display.width = 100
    pd.options.mode.chained_assignment = None