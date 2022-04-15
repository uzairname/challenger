import re
import numpy as np


class InputParser():

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

__all__ = ["InputParser"]