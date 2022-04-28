import hikari
import tanjun
import time
from datetime import datetime, timedelta
import functools

from Challenger.helpers import *
from Challenger.database import Guild_DB
from Challenger.config import *



component = tanjun.Component(name="misc module")




@component.with_command
@tanjun.as_slash_command("ping", "get info about the bot's ping and uptime", always_defer=True)
async def ping_command(ctx:tanjun.abc.Context, client:tanjun.abc.Client=tanjun.injected(type=tanjun.abc.Client)):
    start_time = time.perf_counter()

    start_db = time.perf_counter()
    DB = Guild_DB(ctx.guild_id)
    DB.get_config()
    DB_time = (time.perf_counter() - start_db) * 1000

    heartbeat_latency = ctx.shards.heartbeat_latency * 1_000 if ctx.shards else float("NAN")

    rest_start = time.perf_counter()
    await ctx.rest.fetch_my_user()
    rest_time = (time.perf_counter() - rest_start) * 1000

    total = (time.perf_counter() - start_time) * 1_000

    time_diff = datetime.now() - client.metadata["start_time"]
    response = f"> Database: {DB_time:.0f}ms\n> Rest: {rest_time:.0f}ms\n> Gateway: {heartbeat_latency:.0f}ms\n"
    response += "Time since last startup: " + str(timedelta(seconds=time_diff.total_seconds())) + "\n"

    embed = hikari.Embed(title="PONG!", description=response, color=Colors.PRIMARY)

    await ctx.respond(embed=embed)


@tanjun.as_slash_command("elo-stats", "the server's elo stats", always_defer=True)
async def elo_stats(ctx):
    DB = Guild_DB(ctx.guild_id)

    all_players = DB.get_players()

    avg_elo = all_players[all_players["is_ranked"]].mean()["elo"]
    std_elo = all_players[all_players["is_ranked"]].std()["elo"]
    median_elo = all_players[all_players["is_ranked"]].median()["elo"]

    embed = hikari.Embed(title="Elo Stats For Server", description=f"Avg elo: {avg_elo:.2f}\n"
                                                                   f"Std elo: {std_elo:.2f}\n"
                                                                   f"Median elo: {median_elo:.2f}", color=Colors.PRIMARY)
    embed.add_field("Params", f"Starting elo: {Elo.STARTING_ELO}\n"
                              f"Scale: {Elo.SCALE}\n"
                              f"k: {Elo.K}")

    await ctx.respond(embed=embed)


@tanjun.as_slash_command("refresh-all-matches", "recalculate the elo for every match", default_to_ephemeral=False)
@ensure_staff
async def recalculate_all_matches(ctx: tanjun.abc.SlashContext, bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot)) -> None:

    await ctx.respond("Getting matches...")

    DB = Guild_DB(ctx.guild_id)
    all_matches = DB.get_matches()

    await ctx.edit_initial_response("Recalculating matches...")

    all_players = DB.get_players()
    reduced_players_df = all_players[["elo", "is_ranked"]]
    reduced_players_df["elo"] = Elo.STARTING_ELO

    start_time = time.perf_counter()
    updated_matches, updated_players = recalculate_matches(all_matches, match_id=1, updated_players=reduced_players_df, update_all=True)
    print("calculate matches time taken:" + str(time.perf_counter() - start_time))

    start_time = time.perf_counter()
    DB.upsert_matches(updated_matches)
    players = DB.get_players(user_ids=list(updated_players.index))

    players_before = players.loc[updated_players.index, updated_players.columns]
    players[updated_players.columns] = updated_players
    DB.upsert_players(players)


    # shows the result
    updated_players_strs = []
    for user_id, updated_player in updated_players.iterrows():

        prior_elo_str = str(round(players_before.loc[user_id, "elo"]))
        if not players_before.loc[user_id, "is_ranked"]:
            prior_elo_str += "?"

        updated_elo_str = str(round(updated_player["elo"]))
        if not updated_player["is_ranked"]:
            updated_elo_str += "?"

        updated_players_strs.append("<@" + str(user_id) + "> " + prior_elo_str + " -> " + updated_elo_str + "\n")

    print("upsert players time taken:" + str(time.perf_counter() - start_time))


    start_time = time.perf_counter()
    await ctx.edit_initial_response("Updating elo roles...")
    async for message in update_players_elo_roles(ctx, bot, updated_players):
        await ctx.edit_last_response(message)
    print("update players elo roles time taken:" + str(time.perf_counter() - start_time))


    done_str = "All matches and elo were updated based on match results and any new elo config settings"
    def get_updated_players_for_page(page_num):
        page_size = 10
        start_index = page_size * page_num
        end_index = start_index + page_size

        if page_num < 0:
            return None

        if end_index > len(updated_players_strs):
            end_index = len(updated_players_strs)

        if start_index >= end_index:
            return None

        embed = hikari.Embed(title="updated elo", description=''.join(updated_players_strs[start_index:end_index]), color=Colors.PRIMARY)
        return embed

    def is_last_page(page_num):
        return get_updated_players_for_page(page_num + 1) is None

    await ctx.edit_initial_response(done_str)

    cur_page = 0
    while True:
        await ctx.get_channel().send(embed=get_updated_players_for_page(cur_page))
        if is_last_page(cur_page):
            break
        cur_page += 1





misc = tanjun.Component(name="misc", strict=True).load_from_scope().make_loader()