import hikari
from Challenger.config import *


class Embed_Type:
    ERROR = 1
    CONFIRM = 2
    CANCEL = 3
    INFO = 4




class Custom_Embed(hikari.Embed):

    def __init__(self, type, title=None, description=None, url=None, color=None, colour=None, timestamp=None):

        if type == Embed_Type.ERROR:
            super().__init__(color=color or Colors.ERROR, title=title or "Error", description=description or "Error.", url=url, timestamp=timestamp)
        elif type == Embed_Type.CONFIRM:
            super().__init__(color=color or Colors.SUCCESS, title=title or "Confirmed", description=description or "Confirmed.", url=url, timestamp=timestamp)
        elif type == Embed_Type.CANCEL:
            super().__init__(color=color or Colors.NEUTRAL, title=title or "Cancelled", description=description or "Cancelled.", url=url, timestamp=timestamp)
        elif type == Embed_Type.INFO:
            super().__init__(color=color or Colors.PRIMARY, title=title or "Info", description=description, url=url, timestamp=timestamp)