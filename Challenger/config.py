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
    QUEUE_JOIN_TIMEOUT = 300

@final
class Elo:

    ELO_STDEV = 150  # estimate of standard deviation of everyone's elo
    DEFAULT_ELO = 1000  # everyone's starting score
    DEFAULT_SCALE = ELO_STDEV * 2.7  # Used in elo calculation. 2.7 is an arbitrary scaling factor
    DEFAULT_K = 30  # maximum change in one game
    NUM_UNRANKED_MATCHES = 2  # number of matches to play before ranking


@final
class Database_Config:

    # known names for some known discord servers, for ease of use. testing is for unit testing
    KNOWN_GUILDS = {1: "testing", Config.DEV_GUILD_ID: "development", 947184983120957452: "PX", 921447683154145331:"B2T"}