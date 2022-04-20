import os
from typing import final
from hikari import Permissions


@final
class Config:

    VERSION = '1.0.0'

    GITHUB_LINK = "https://github.com/lilapela/competition"
    OWNER_ID = 623257053879861248  # Lilapela's ID
    DEV_GUILD_ID = 907729885726933043 # lilap
    DISCORD_INVITE_LINK = "https://discord.gg/bunZ3gadBU"

    REQUIRED_PERMISSIONS = Permissions.VIEW_CHANNEL | Permissions.SEND_MESSAGES | Permissions.EMBED_LINKS | Permissions.MANAGE_ROLES
    PERMS_ERR_MSG = f"The bot is missing some required permissions. Type /about to see them"
    if os.environ.get("ENVIRONMENT") == "development":
        INVITE_LINK = "https://discord.com/api/oauth2/authorize?client_id=951132825803964447&permissions=" + str(REQUIRED_PERMISSIONS.value) + "&scope=bot%20applications.commands"
    elif os.environ.get("ENVIRONMENT") == "production":
        INVITE_LINK =  "https://discord.com/api/oauth2/authorize?client_id=908432840566374450&permissions=" + str(REQUIRED_PERMISSIONS.value) + "&scope=bot%20applications.commands"

    COMPONENT_TIMEOUT = 120
    QUEUE_JOIN_TIMEOUT = 600


@final
class Elo:

    STD = 20
    # The wanted standard deviation of everyone's elo

    STARTING_ELO = 100
    # Everyone's starting elo, also everyone's average elo

    SCALE = STD * 2.7
    # Used in elo calculation. 2.7 is a hyperparameter, I think it just tries to ensure that the actual std matches the
    # wanted std. in standard chess its 2.66

    K = STD / 4
    # Maximum change in one game. 4 is a hyperparameter. I think it means something like how volatile elo change is,
    # while not affecting long term spread. It's 5 for chess

    NUM_PLACEMENT_MATCHES = 3  # How many of the first games are scored by provisional elo


@final
class Database_Config:

    # database names for some known discord servers, for ease of use. "testing" is for unit testing
    KNOWN_GUILDS = {1: "testing", Config.DEV_GUILD_ID: "development", 947184983120957452: "PX", 921447683154145331:"B2T"}