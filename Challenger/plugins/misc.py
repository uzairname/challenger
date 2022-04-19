import hikari
import tanjun
import time
from datetime import datetime, timedelta
import functools

from Challenger.utils import *
from Challenger.database import Session

component = tanjun.Component(name="misc module")


def measure_time(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        await func(start_time=start_time, *args, **kwargs)
    return wrapper

@component.with_command
@tanjun.as_slash_command("ping", "get info about the bot's ping and uptime", always_defer=True)
@measure_time
async def ping_command(ctx:tanjun.abc.Context, client:tanjun.abc.Client=tanjun.injected(type=tanjun.abc.Client), **kwargs):
    start_time = time.perf_counter()

    start_db = time.perf_counter()
    DB = Session(ctx.guild_id)
    DB_time = (time.perf_counter() - start_db) * 1000

    heartbeat_latency = ctx.shards.heartbeat_latency * 1_000 if ctx.shards else float("NAN")

    rest_start = time.perf_counter()
    await ctx.rest.fetch_my_user()
    rest_time = (time.perf_counter() - rest_start) * 1000

    total = (time.perf_counter() - start_time) * 1_000

    time_diff = datetime.now() - client.metadata["start_time"]
    response = f"> Database: {DB_time:.0f}ms\n> Rest: {rest_time:.0f}ms\n> Gateway: {heartbeat_latency:.0f}ms\n"
    response += "Bot has been online for: " + str(timedelta(seconds=time_diff.total_seconds())) + "\n"

    embed = hikari.Embed(title="PONG!", description=response, color=Colors.PRIMARY)

    await ctx.respond(embed=embed)


@tanjun.as_slash_command("refresh-all-matches", "recalculate the elo for every match", default_to_ephemeral=False)
@ensure_staff
async def recalculate_all_matches(ctx: tanjun.abc.SlashContext, bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot)) -> None:

    await ctx.respond("Getting matches...")

    DB = Session(ctx.guild_id)
    all_matches = DB.get_matches()

    await ctx.respond("Recalculating matches...")

    print(all_matches)

    updated_matches, updated_players = update_matches(all_matches, match_id=1, update_all=True)
    DB.upsert_matches(updated_matches)

    players = DB.get_players(user_ids=list(updated_players.index))
    players_before = players.loc[updated_players.index, updated_players.columns]
    players[updated_players.columns] = updated_players

    updated_players_str = ""
    for id, row in updated_players.iterrows():
        prior_elo_str = str(round(players_before.loc[id, "elo"]))
        if not players_before.loc[id, "is_ranked"]:
            prior_elo_str += "?"

        updated_elo_str = str(round(updated_players.loc[id, "elo"]))
        if not updated_players.loc[id, "is_ranked"]:
            updated_elo_str += "?"

        updated_players_str += "<@" + str(id) + "> " + prior_elo_str + " -> " + updated_elo_str + "\n"
        await update_player_elo_roles(ctx, bot, id)


    DB.upsert_players(players)
    explanation_str = "All matches and elo were updated based on match results and any new elo config settings"

    embed = hikari.Embed(title="REFRESHED ALL MATCHES", description=explanation_str, color=Colors.PRIMARY)
    embed.add_field(name="Updated players", value=updated_players_str)

    await ctx.edit_initial_response(embed=embed)



misc = tanjun.Component(name="misc", strict=True).load_from_scope().make_loader()