import os
from bot import build_bot
import logging
from database import *


if __name__ == "__main__":
    config_database()

    build_bot().run()