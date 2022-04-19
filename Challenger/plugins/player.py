import tanjun
import hikari

from datetime import datetime

from Challenger.utils import *
from Challenger.database import Session
from Challenger.config import *

component = tanjun.Component(name="player module")



@component.with_slash_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.as_slash_command("register", "Join the fun!", default_to_ephemeral=True)
async def register(ctx: tanjun.abc.Context) -> None:

    await ctx.respond("please wait")

    DB = Session(ctx.guild_id)
    player_id = ctx.author.id
    players = DB.get_players(user_id=player_id)

    tag = ctx.author.username + "#" + ctx.author.discriminator
    name = ctx.member.nickname or ctx.member.username

    if players.empty:
        player = DB.get_new_player(ctx.author.id)
        player["username"] = name
        player["tag"] = tag
        player["time_registered"] = datetime.now()
        player["is_ranked"] = False
        player["elo"] = Elo.DEFAULT_ELO
        DB.upsert_player(player)
        await ctx.get_channel().send(f"{ctx.author.mention} has registered! :)", user_mentions=True)
        return

    player = players.iloc[0]
    player["username"] = name
    player["tag"] = tag
    DB.upsert_player(player)
    await ctx.edit_initial_response("You've already registered. Updated your username")


@component.with_slash_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.with_member_slash_option("player", "(optional) their mention", default=None)
@tanjun.as_slash_command("stats", "view your or someone's stats", default_to_ephemeral=False, always_defer=True)
async def get_stats(ctx: tanjun.abc.Context, player) -> None:

    DB = Session(ctx.guild_id)

    #get the selected player
    if player:
        member = player
        players = DB.get_players(user_id=player.id)
    else:
        member = ctx.member
        players = DB.get_players(user_id=ctx.author.id)

    try:
        player = players.iloc[0]
    except IndexError:
        await ctx.edit_initial_response("This player isn't registered")
        return

    matches = DB.get_matches(user_id=player.name)

    total_draws = 0
    total_wins = 0
    total_losses = 0
    for index, match in matches.iterrows():
        if match["outcome"] == Outcome.DRAW:
            total_draws += 1

        winning_result = Outcome.PLAYER_1 if match["p1_id"] == player.name else Outcome.PLAYER_2
        losing_result = Outcome.PLAYER_2 if match["p1_id"] == player.name else Outcome.PLAYER_1

        if match["outcome"] == winning_result:
            total_wins += 1
        elif match["outcome"] == losing_result:
            total_losses += 1

    total = total_wins + total_losses + total_draws

    displayed_elo = str(round((player["elo"]),2))
    if not player["is_ranked"]:
        displayed_elo += "? (unranked)"

    stats_embed = Custom_Embed(type=Embed_Type.INFO, title=f"{player['tag']}'s Stats", description="*_ _*", color=member.accent_color).set_thumbnail(member.avatar_url)
    stats_embed.add_field(name="Elo", value=displayed_elo)
    stats_embed.add_field(name="Total matches", value=f"{total}")
    stats_embed.add_field(name="Wins", value=f"{total_wins}", inline=True)
    stats_embed.add_field(name="Draws", value=f"{total_draws}", inline=True)
    stats_embed.add_field(name="Losses", value=f"{total_losses}", inline=True)

    await ctx.edit_initial_response(embed=stats_embed)


@component.with_slash_command
@tanjun.with_own_permission_check(Config.REQUIRED_PERMISSIONS, error_message=Config.PERMS_ERR_MSG)
@tanjun.as_slash_command("lb", "leaderboard", default_to_ephemeral=False, always_defer=True)
async def get_leaderboard(ctx: tanjun.abc.Context, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot)) -> None:

    response = await ctx.fetch_initial_response()

    DB = Session(ctx.guild_id)

    def get_leaderboard_for_page(page):

        players_per_page = 20
        max_name_len = 30

        if page < 0:
            return None

        players = DB.get_players(by_elo=True, ranked=True, limit=players_per_page, skip=page * players_per_page)

        if players.index.size == 0:
            if page == 0:
                return [hikari.Embed(title="Leaderboard", description="No ranked players", color=Colors.PRIMARY)]
            return None

        place = page * players_per_page

        lb_list = "```\n"
        for index, player, in players.iterrows():
            place += 1
            tag = str(player["tag"])[:max_name_len]
            lb_list += str(place) + "." + " "*(5-len(str(place))) + tag + ": "  + " "*(max_name_len-len(tag))  + str(round(player["elo"])) + "\n"
        lb_list += "```"

        lb_embed = hikari.Embed(title="Leaderboard", description=f"Leaderboard page {page + 1}", color=Colors.PRIMARY)
        lb_embed.add_field(name="Rank       Username                                                  Score", value=lb_list, inline=False)
        lb_embed.set_footer(text="Don't see yourself? Only players who completed their " + str(Elo.NUM_UNRANKED_MATCHES) + " provisional games are ranked")
        return [lb_embed]

    await create_paginator(ctx, bot, response, get_leaderboard_for_page, nextlabel="Lower", prevlabel="Higher")


player = tanjun.Component(name="player", strict=True).load_from_scope().make_loader()