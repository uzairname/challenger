import os

from bot.py import build_bot

if os.name != "nt":
    import uvloop

    uvloop.install()

if __name__ == "__main__":
    build_bot.run()