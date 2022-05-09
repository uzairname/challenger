# hi

import hikari
import os

from Challenger.bot import build_bot
from Challenger.config import set_pandas_display_options

import mongoengine as me

if __name__ == "__main__":

    set_pandas_display_options()

    if os.environ.get("ENVIRONMENT") == "development":
        me.connect("development", host=os.environ.get("MONGODB_URL"))

    build_bot(os.environ.get('DISCORD_TOKEN')).run(status=hikari.Status.DO_NOT_DISTURB)
