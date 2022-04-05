from utils.utils import *
import hikari
from database import Database
from datetime import datetime
from utils.ELO import *

component = tanjun.Component(name="player module")


async def ensure_registered(ctx: tanjun.abc.Context, DB:Database):
    player_info = DB.get_players(user_id=ctx.author.id)
    if player_info.empty:
        await ctx.respond(f"hello {ctx.author.mention}. Please register with /register to play", user_mentions=True)
        return None
    return player_info


@component.with_slash_command
@tanjun.as_slash_command("register", "Join the fun!", default_to_ephemeral=True)
async def register(ctx: tanjun.abc.Context) -> None:

    await ctx.respond("please wait")

    DB = Database(ctx.guild_id)
    player_id = ctx.author.id
    players = DB.get_players(user_id=player_id)

    tag = ctx.author.username + "#" + ctx.author.discriminator

    if ctx.member.nickname is not None:
        name = ctx.member.nickname
    else:
        name = ctx.author.username

    if players.empty:
        player = DB.get_new_player(ctx.author.id)
        player["username"] = name
        player["tag"] = tag
        player["time_registered"] = datetime.now()
        player["is_ranked"] = False
        player["elo"] = DEFAULT_ELO
        player["staff"] = status.NONE
        DB.upsert_player(player)
        await ctx.get_channel().send(f"{ctx.author.mention} has registered! :)", user_mentions=True)
        return

    player = players.iloc[0]
    player["username"] = name
    player["tag"] = tag
    DB.upsert_player(player)
    await ctx.edit_initial_response("You've already registered. Updated your username")


@component.with_slash_command
@tanjun.with_str_slash_option("player", "their mention", default=None)
@tanjun.as_slash_command("stats", "view your stats", default_to_ephemeral=True)
async def get_stats(ctx: tanjun.abc.Context, player) -> None:

    await ctx.respond("plese wait")

    DB = Database(ctx.guild_id)

    #get the selected player
    if player:
        input_users = InputParams(str(player)).users
        if len(input_users) != 1:
            await ctx.edit_initial_response("Enter a valid player id")
            return

        players = DB.get_players(user_id=input_users[0])
        if players.empty:
            await ctx.edit_initial_response("Unknown or unregistered player")
            return
        player = players.iloc[0]
    else:
        player = await ensure_registered(ctx, DB)
        if player is None:
            return
        player = player.iloc[0]


    matches = DB.get_matches(user_id=player["user_id"])

    total_draws = 0
    total_wins = 0
    total_losses = 0
    for index, match in matches.iterrows():
        if match["outcome"] == results.DRAW:
            total_draws += 1

        winning_result = results.PLAYER_1 if match["player_1"] == player["user_id"] else results.PLAYER_2
        losing_result = results.PLAYER_2 if match["player_1"] == player["user_id"] else results.PLAYER_1

        if match["outcome"] == winning_result:
            total_wins += 1
        elif match["outcome"] == losing_result:
            total_losses += 1


    displayed_elo = str(round((player["elo"]),2))
    if not player["is_ranked"]:
        displayed_elo += " (unranked)"

    stats_embed = hikari.Embed(title=f"{player['tag']}", description="Stats", color=Colors.PRIMARY)
    stats_embed.add_field(name="Elo", value=displayed_elo)
    stats_embed.add_field(name="Total matches", value=f"{matches.shape[0]}")
    stats_embed.add_field(name="Wins", value=f"{total_wins}", inline=True)
    stats_embed.add_field(name="Losses", value=f"{total_losses}", inline=True)
    stats_embed.add_field(name="Draws", value=f"{total_draws}", inline=True)

    await ctx.get_channel().send(embed=stats_embed)


@component.with_slash_command
@tanjun.as_slash_command("lb", "leaderboard", default_to_ephemeral=False)
async def get_leaderboard(ctx: tanjun.abc.Context) -> None:

    await ctx.respond("please wait")

    DB = Database(ctx.guild_id)

    players = DB.get_players(top_by_elo=[0,20])
    if players.empty:
        await ctx.edit_initial_response("No players registered")
        return

    ranked_players = players.loc[players["is_ranked"]==True]
    unranked_players = players.loc[players["is_ranked"]==False]

    max_len = 25
    ranked_list = "```\n"
    place = 0
    for index, player, in ranked_players.iterrows():
        place += 1
        tag = str(player["tag"])[:max_len]
        ranked_list += str(place) + "." + " "*(5-len(str(place))) + tag + ": "  + " "*(max_len-len(tag))  + str(round(player["elo"])) + "\n"

    ranked_list += "```"

    unranked_list = "```\n"
    unranked_players.sort_values(by="elo", ascending=True, inplace=True)
    place = 0
    for index, player in unranked_players.iterrows():
        place += 1
        tag = str(player["tag"])[:max_len]
        unranked_list += str(place) + "." + " "*(5-len(str(place))) + tag + ": "  + " "*(max_len-len(tag))  + str(round(player["elo"])) + "?\n"

    unranked_list += "```"

    ranked_embed = hikari.Embed(title="Leaderboard", description="Page 1: Top 20", color=Colors.PRIMARY)
    ranked_embed.add_field(name="Rank       Username                                                  Score", value=ranked_list, inline=False)

    unranked_embed = hikari.Embed(title="Unranked Leaderboard", description="Players' first few games are scored by provisional elo.\nPage 1: Top 20", color=Colors.PRIMARY)
    unranked_embed.add_field(name="Rank       Username                                                  Score", value=unranked_list, inline=False)

    await ctx.edit_initial_response("", embeds=[ranked_embed, unranked_embed])





@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())