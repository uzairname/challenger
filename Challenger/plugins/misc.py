import tanjun
import time
from datetime import datetime, timedelta

from Challenger.utils import *
from Challenger.database import Session

component = tanjun.Component(name="misc module")


def measure_time(func):
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        await func(start_time=start_time, *args, **kwargs)
    return wrapper

@tanjun.as_slash_command("bot-status", "get info about the bot's ping and uptime", always_defer=True)
@measure_time
async def bot_status_command(ctx:tanjun.abc.Context, start_time, client=tanjun.injected(type=tanjun.abc.Client)):

    start_db = time.perf_counter()
    DB = Session(ctx.guild_id)
    DB_time = (time.perf_counter() - start_db) * 1000

    heartbeat_latency = ctx.shards.heartbeat_latency * 1_000 if ctx.shards else float("NAN")

    rest_start = time.perf_counter()
    await ctx.rest.fetch_my_user()
    rest_time = (time.perf_counter() - rest_start) * 1000

    total = (time.perf_counter() - start_time) * 1_000

    response = ""

    time_diff = datetime.now() - client.metadata["start_time"]
    response += f"PONG\n - Database: {DB_time:.0f}ms\n - Rest: {rest_time:.0f}ms\n - Gateway: {heartbeat_latency:.0f}ms\n"
    response += "Bot has been online for: " + str(timedelta(seconds=time_diff.total_seconds())) + "\n"

    await ctx.respond(response)




misc = tanjun.Component(name="misc", strict=True).load_from_scope().make_loader()