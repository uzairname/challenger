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


class Elo:

    STARTING_ELO = 100
    # Everyone's starting elo, also everyone's average elo


    SCALE = 40
    # The elo difference which represents a 10x difference in skill. Used in elo calculation.
    # The coefficient is a hyperparameter. I think it just tries to ensure that the actual std matches the wanted std


    K_COEF = 0.15
    K = SCALE * K_COEF
    # Maximum change in one game

    STD = SCALE*0.69 #estimated standard deviation

    #maybe k can be dependent on scale and wanted std. f(scale, wanted_std ) = k so that actual std is the wanted std

    NUM_PLACEMENT_MATCHES = 3  # How many of the first games are scored by provisional elo


@final
class Database_Config:

    B2T_GUILD_ID = 921447683154145331

    # database names for some known discord servers, for ease of use. "testing" is for unit testing
    KNOWN_GUILDS = {1: "testing", Config.DEV_GUILD_ID: "development", 947184983120957452: "PX", B2T_GUILD_ID:"B2T"}