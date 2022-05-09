import hikari
import tanjun
import time
from datetime import datetime, timedelta
import functools

from Challenger.helpers import *
from Challenger.database import *
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


@tanjun.with_str_slash_option("leaderboard", "the leaderboard")
@tanjun.as_slash_command("refresh-all-matches", "recalculate the elo for every match", default_to_ephemeral=False)
@ensure_staff
async def recalculate_all_matches(ctx: tanjun.abc.SlashContext, leaderboard, bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot)) -> None:
    leaderboard_name = leaderboard

    await ctx.respond("Getting matches...")

    all_matches = Match.objects(guild_id=ctx.guild_id, leaderboard_name=leaderboard_name)
    all_players = Player.objects(guild_id=ctx.guild_id, leaderboard_name=leaderboard_name)

    await ctx.edit_initial_response("Recalculating matches...")
    all_matches_df = pd.DataFrame([a.to_mongo() for a in all_matches]).set_index("match_id").replace(np.nan, None)
    players_before = pd.DataFrame([a.to_mongo() for a in all_players]).set_index("_id").replace(np.nan, None)

    players_reset = players_before.copy()
    players_reset["elo"] = Elo.STARTING_ELO
    players_reset["RD"] = Elo.STARTING_RD
    updated_matches, updated_players = recalculate_matches(all_matches_df, 1, updated_players=players_reset)

    affected_players = updated_players.index.union(players_before.index)


    # update database
    await ctx.edit_initial_response("Updating Matches...")
    for player_id, p in updated_players.iterrows():
        print(player_id)
        Player.objects.with_id(player_id).update(set__elo=p["elo"], set__RD=p["RD"])

    for match_id, m in updated_matches.iterrows():
        Match.objects(guild_id=ctx.guild_id, leaderboard_name=leaderboard_name, match_id=match_id).update(set__outcome=m['outcome'], set__player_1_elo=m['player_1_elo'], set__player_2_elo=m['player_2_elo'], set__player_1_RD=m['player_1_RD'], set__player_2_RD=m['player_2_RD'])


    # show the result
    updated_players_strs = []
    for _id, player in players_before.iterrows():
        prior_elo_str = str(round(player["elo"]))
        updated_elo_str = str(round(updated_players.loc[_id,"elo"]))
        updated_players_strs.append("<@" + str(player["user_id"]) + "> " + prior_elo_str + " -> " + updated_elo_str + "\n")


    #update elo roles

    # await ctx.edit_initial_response("Updating elo roles...")
    # async for message in update_players_elo_roles(ctx, bot, updated_players):
    #     await ctx.edit_last_response(message)

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