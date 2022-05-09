import hikari
import tanjun

import asyncio
from datetime import datetime

from Challenger.config import *
from Challenger.utils import calc_elo_change
from Challenger.database import *


async def remove_from_q_timeout(guild_id, leaderboard_name, channel_id, ctx:tanjun.abc.Context):
    await asyncio.sleep(App.QUEUE_JOIN_TIMEOUT)

    guild = Guild.objects.filter(guild_id=guild_id).first()
    guild.leaderboards.filter(name=leaderboard_name).first().lobbies.filter(channel_id=channel_id).first().player_in_q = None
    guild.save()

    await ctx.respond("You have been removed from the queue")
    await ctx.get_channel().send("A player was removed from the queue after " + str(App.QUEUE_JOIN_TIMEOUT // 60) + " minutes")


def remove_from_queue(guild_id, leaderboard_name, channel_id):

    guild = Guild.objects.filter(guild_id=guild_id).first()
    guild.leaderboards.filter(name=leaderboard_name).first().lobbies.filter(channel_id=channel_id).first().player_in_q = None
    guild.save()

    for i in asyncio.all_tasks():
        if i.get_name() == get_timeout_name(guild_id, leaderboard_name, channel_id):
            i.cancel()


def get_timeout_name(guild_id, leaderboard_name, channel_id):
    return str(guild_id)+str(channel_id) + leaderboard_name + "_queue_timeout"




def describe_match(match:pd.Series) -> hikari.Embed:

    start_time = time.time()
    p1_username = Player.objects(id=match["player_1"]).first().username
    p2_username = Player.objects(id=match["player_2"]).first().username
    print("get 2 players took " + str(time.time() - start_time))

    def get_elo_str(elo, is_ranked):
        if elo is None:
            return "?"
        if is_ranked:
            return str(round(elo))
        else:
            return str(round(elo)) + "?"


    p1_elo_before_displayed = get_elo_str(match["player_1_elo"], True)
    p2_elo_before_displayed = get_elo_str(match["player_2_elo"], True)

    p1_is_ranked_before = determine_is_ranked()
    p2_is_ranked_before = determine_is_ranked()
    elo_change = calc_elo_change(match["player_1_elo"], match["player_2_elo"], match["outcome"], p1_is_ranked_before, p2_is_ranked_before)
    p1_elo_after = match["player_1_elo"] + elo_change[0]
    p2_elo_after = match["player_2_elo"] + elo_change[1]
    p1_is_ranked_after = determine_is_ranked()
    p2_is_ranked_after = determine_is_ranked()

    p1_elo_after_displayed = get_elo_str(p1_elo_after, p1_is_ranked_after)
    p2_elo_after_displayed = get_elo_str(p2_elo_after, p2_is_ranked_after)

    if match["outcome"] in PLAYED:
        p1_elo_change = 0
        p2_elo_change = 0
        p1_elo_indicator = "▲" if p1_elo_change > 0 else "▼" if p1_elo_change < 0 else ""
        p2_elo_indicator = "▲" if p2_elo_change > 0 else "▼" if p2_elo_change < 0 else ""
        p1_elo_diff_str = str(round(abs(p1_elo_change)))
        p2_elo_diff_str = str(round(abs(p2_elo_change)))
        p1_elo_change_str = "> " + str(p1_elo_before_displayed) + " -> **" + str(p1_elo_after_displayed) \
                            + "** *(" + p1_elo_indicator + p1_elo_diff_str + ")*"
        p2_elo_change_str = "> " + str(p2_elo_before_displayed) + " -> **" + str(p2_elo_after_displayed) \
                            + "** *(" + p2_elo_indicator + p2_elo_diff_str + ")*"

    else:
        p1_elo_change_str = ""
        p2_elo_change_str = ""

    color = Colors.SUCCESS
    if match["outcome"] == Outcome.PLAYER_1:
        outcome_str = p1_username + " won"
    elif match["outcome"] == Outcome.PLAYER_2:
        outcome_str = p2_username + " won"
    elif match["outcome"] == Outcome.CANCELLED:
        outcome_str = "Cancelled"
        color = Colors.DARK
    elif match["outcome"] == Outcome.DRAW:
        outcome_str = "Draw"
    else:
        outcome_str = "Undecided"
        color = Colors.WARNING

    if match["player_1_declared"] == Outcome.PLAYER_1:
        p1_declared = "Declared win"
    elif match["player_1_declared"] == Outcome.PLAYER_2:
        p1_declared = "Declared loss"
    elif match["player_1_declared"] is None:
        p1_declared = "Didn't declare"
    else:
        p1_declared = match["player_1_declared"]
    if match["player_2_declared"] == Outcome.PLAYER_2:
        p2_declared = "Declared win"
    elif match["player_2_declared"] == Outcome.PLAYER_1:
        p2_declared = "Declared loss"
    elif match["player_2_declared"] is None:
        p2_declared = "Didn't declare"
    else:
        p2_declared = match["player_2_declared"]


    embed = hikari.Embed(title="Match " + str(match.name), color=color)

    embed.add_field(name=outcome_str, value=BLANK)
    embed.add_field(name=str(p1_username), value=p1_elo_change_str + "\n> " + p1_declared, inline=True)
    embed.add_field(name="vs", value=BLANK, inline=True)
    embed.add_field(name=str(p2_username), value=p2_elo_change_str + "\n> " + p2_declared, inline=True)

    embed.set_footer(text=match["time_started"].strftime("%B %d, %Y, %H:%M") + " UTC")

    return embed



async def start_announce_new_match(ctx:tanjun.abc.Context, p1_info, p2_info):
    """creates a new match between the 2 players and announces it to the channel"""

    DB = Guild_DB(ctx.guild_id)
    new_match = DB.get_new_match()
    DB.upsert_match(new_match)

    p1_ping = "<@" + str(p1_info.name) + ">"
    p2_ping = "<@" + str(p2_info.name) + ">"

    p1_is_ranked = p1_info["is_ranked"]
    p2_is_ranked = p2_info["is_ranked"]


    new_match[["time_started", "p1_id", "p2_id", "p1_elo", "p2_elo", "p1_is_ranked", "p2_is_ranked"]] = \
        [datetime.now(), p1_info.name, p2_info.name, p1_info["elo"], p2_info["elo"], p1_is_ranked, p2_is_ranked]


    embed = hikari.Embed(title="Match " + str(new_match.name) + " started", description=p1_info["tag"] + " vs " + p2_info["tag"], color=Colors.PRIMARY)

    await ctx.get_channel().send(content=p1_ping+ " " + p2_ping, embed=embed, user_mentions=True)



async def announce_in_updates_channel(ctx, embed, client:tanjun.Client, content=None):
    DB = Guild_DB(ctx.guild_id)

    config = DB.get_config()
    channel_id = config["results_channel"]

    if channel_id is None:

        embed.set_footer(text="ℹ Announcing here because no match announcements channel is set. Type /config match-updates-channel to set one.")
        await ctx.get_channel().send(embed=embed)
        return
    await client.rest.create_message(channel_id, content=content, embed=embed, user_mentions=True)


async def update_players_elo_roles(ctx:tanjun.abc.Context, bot:hikari.GatewayBot, players:pd.DataFrame, role_ids=None):
    """
    Needs a message context to send an error message if the bot doesn't have role perms.
    players: dataframe with index user id and columns elo and is_ranked
    roles: list of role ids
    """

    DB = Guild_DB(ctx.guild_id)
    elo_roles = DB.get_elo_roles()
    if role_ids:
        elo_roles = elo_roles[elo_roles.index.isin(role_ids)]

    players_updated = 0

    try:
        for user_id, player in players.iterrows():

            players_updated += 1
            yield  "updating elo roles (" + str(round(100 * players_updated / players.shape[0])) + "%)"

            try:
                current_roles = (await ctx.rest.fetch_member(ctx.guild_id, user_id)).get_roles()
            except hikari.NotFoundError:
                continue

            current_roles = [role.id for role in current_roles]

            for role_id, role_info in elo_roles.iterrows():

                if not player["is_ranked"]:

                    if role_id in current_roles:
                        await bot.rest.remove_role_from_member(ctx.guild_id, user_id, role_id)

                    continue

                if role_info["min_elo"] <= player["elo"] <= role_info["max_elo"]:

                    if not role_id in current_roles:
                        await bot.rest.add_role_to_member(ctx.guild_id, user_id, role_id)

                else:
                    if role_id in current_roles:
                        await bot.rest.remove_role_from_member(ctx.guild_id, user_id, role_id)

    except hikari.ForbiddenError:
        await ctx.respond(embed=Custom_Embed(type=Embed_Type.ERROR, title="Unable to update roles", description="Please make sure the bot's role is above all elo roles"))

    yield "done"


def player_col_for_match(match, user_id, column, opponent=False): #useful probably

    if (match["p1_id"] == user_id) == (not opponent):

        return match["p1_" + column]
    elif (match["p2_id"] == user_id) == (not opponent):
        return match["p2_" + column]
    else:
        raise ValueError("Player not in match")

__all__ = ["describe_match", "announce_in_updates_channel", "update_players_elo_roles", "remove_from_q_timeout", "remove_from_queue", "determine_is_ranked", "player_col_for_match", "start_announce_new_match", "get_timeout_name"]