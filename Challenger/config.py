import typing
import hikari


@typing.final
class Config:
    """
    Config class.
    """
    OWNER_ID = 623257053879861248  # Lilapela's ID
    TESTING_GUILD_ID = 907729885726933043
    PX_GUILD_ID = 947184983120957452
    TESTING_INVITE_LINK = "https://discord.com/api/oauth2/authorize?client_id=951132825803964447&permissions=544857254992&scope=bot%20applications.commands"
    INVITE_LINK = "https://discord.com/api/oauth2/authorize?client_id=908432840566374450&permissions=544857254992&scope=bot%20applications.commands"

    ELO_STDEV = 150  # estimate of standard deviation of everyone's elo
    DEFAULT_ELO = 1000  # everyone's starting score
    DEFAULT_SCALE = ELO_STDEV * 2.7  # Used in elo calculation. 2.7 is an arbitrary scaling factor
    DEFAULT_K = 30  # maximum change in one game
    NUM_UNRANKED_MATCHES = 2  # number of matches to play before ranking

    DEFAULT_TIMEOUT = 120

    REQUIRED_PERMISSIONS = hikari.Permissions.NONE.SEND_MESSAGES
    PERMS_ERR_MSG = f"Make sure the bot has the following permissions: ```{REQUIRED_PERMISSIONS}```"


@typing.final
class Colors:
    PRIMARY = "#ffc07d" # bronze
    SECONDARY = "#03212e"
    NEUTRAL = "#a5a5a5"
    SUCCESS = "#5dde07"
    ERROR = "#db4737"