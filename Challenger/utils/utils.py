from Challenger.config import *

import numpy as np
import re

class Result:
    PLAYER_1 = "player 1"
    PLAYER_2 = "player 2"
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    CANCEL = "cancelled"
    UNDECIDED = "undecided"

class Declare:
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    CANCEL = "cancel"

class Status:
    NONE = 0
    STAFF = 1

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


class InputParams():
    def __init__(self, input_string):
        text_pat = r"[a-zA-Z\d\s]+"

        channel_pat = r"<#(\d{17,19})>"
        role_pat = r"<@&(\d{17,19})>"
        user_pat = r"<@!?(\d{17,19})>"

        name = re.match(text_pat, input_string)
        if name:
            name = name[0].strip()

        self.channels = np.array(re.findall(channel_pat, input_string)).astype("int64")
        self.roles = np.array(re.findall(role_pat, input_string)).astype("int64")
        self.users = np.array(re.findall(user_pat, input_string)).astype("int64")
        self.text = name

    def describe(self):

        description = ""
        if self.text:
            description += "\nName:\n> " + str(self.text)

        if self.channels.size > 0:
            description += "\nSelected channels:"
            for i in self.channels:
                description += "\n> <#" + str(i) + ">"

        if self.roles.size > 0:
            description += "\nSelected roles:"
            for i in self.roles:
                description += "\n> <@&" + str(i) + ">"

        if self.users.size > 0:
            description += "\nSelected users:"
            for i in self.users:
                description += "\n> <@" + str(i) + ">"

        description += "\n"
        return description

