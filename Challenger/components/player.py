import numpy as np
import tanjun
import hikari

from datetime import datetime

from Challenger.helpers import *
from Challenger.database import *
from Challenger.config import *

component = tanjun.Component(name="player module")



@component.with_slash_command
@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.with_str_slash_option("leaderboard", "the leaderboard to join")
@tanjun.as_slash_command("register", "Join the fun!", default_to_ephemeral=True, always_defer=True)
async def register(ctx: tanjun.abc.Context, leaderboard) -> None:

    leaderboard_name = leaderboard

    user = User.objects(user_id=ctx.author.id).first()
    if user is None:
        user = User(user_id=ctx.author.id, username=ctx.author.username + "#" + ctx.author.discriminator)
        user.save()

    guild = Guild.objects(guild_id=ctx.guild_id).first()

    leaderboard = guild.leaderboards.filter(name=leaderboard_name).first()

    #get the player from the leaderboard if it exists
    player = None
    for p in leaderboard.players:
        if p.user.pk == user.id:
            player = p

    if player is None:
        player = Player(user=user, time_registered=datetime.utcnow(), rating=Elo.STARTING_ELO, rating_deviation=Elo.STARTING_RD)

        print(player.user)
        leaderboard.players.append(player)
        await ctx.get_channel().send(f"{ctx.author.mention} has registered! :)", user_mentions=True)
    else:
        await ctx.respond(f"You've already registered for {leaderboard_name}")


    guild.save()

    return


@component.with_slash_command
@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.with_member_slash_option("player", "(optional) their mention", default=None)
@tanjun.as_slash_command("stats", "view your or someone's stats", default_to_ephemeral=False, always_defer=True)
async def get_stats(ctx: tanjun.abc.Context, player) -> None:

    DB = Guild_DB(ctx.guild_id)

    #get the selected player
    if player:
        member = player
        players = DB.get_players(user_id=player.channel_id)
    else:
        member = ctx.member
        players = DB.get_players(user_id=ctx.author.id)

    try:
        player = players.iloc[0]
    except IndexError:
        await ctx.edit_initial_response("This player isn't registered")
        return

    matches = DB.get_matches(user_id=player.name)
    finished_matches = matches.loc[np.isin(matches["outcome"], Outcome.PLAYED)]

    opponent_elos = []

    for id, match in finished_matches.iterrows():
        opponent_elos.append(player_col_for_match(match, player.name, "elo", opponent=True))

    if len(opponent_elos) == 0:
        avg_opponent_elo_str = "No matches played yet"
    else:
        avg_opponent_elo_str = str(np.mean(opponent_elos).round(2))


    total_draws = 0
    total_wins = 0
    total_losses = 0
    for index, match in finished_matches.iterrows():
        if match["outcome"] == Outcome.DRAW:
            total_draws += 1

        winning_result = Outcome.PLAYER_1 if match["p1_id"] == player.name else Outcome.PLAYER_2
        losing_result = Outcome.PLAYER_2 if match["p1_id"] == player.name else Outcome.PLAYER_1

        if match["outcome"] == winning_result:
            total_wins += 1
        elif match["outcome"] == losing_result:
            total_losses += 1

    total = finished_matches.shape[0]

    displayed_elo = str(round((player["elo"]),1))
    if not player["is_ranked"]:
        displayed_elo += "?"
        displayed_elo_desc = "Unranked"
    else:
        all_players = DB.get_players()
        all_ranked_players = all_players.loc[all_players["is_ranked"] == True]
        place = np.sum(all_ranked_players["elo"] > player["elo"]) + 1
        place_str = convert_to_ordinal(place)
        displayed_elo_desc = place_str + " place"
        if place == 1:
            displayed_elo_desc = "🥇 " + displayed_elo_desc
        elif place == 2:
            displayed_elo_desc = "🥈 " + displayed_elo_desc
        elif place == 3:
            displayed_elo_desc = "🥉 " + displayed_elo_desc

        percentile = np.sum(all_ranked_players["elo"] < player["elo"])/len(all_ranked_players.index) # "less than" percentile
        top_percent = round((1 - percentile)*100)
        displayed_elo_desc += " (top " + str(top_percent) + "%)"



    stats_embed = hikari.Embed(title=f"{player['tag']}'s Stats", color=member.accent_color).set_thumbnail(member.avatar_url)
    stats_embed.add_field(name="Score: " + displayed_elo, value=displayed_elo_desc)
    stats_embed.add_field(name="Average Opponent's elo", value=avg_opponent_elo_str)
    stats_embed.add_field(name="Wins", value=f"{total_wins}", inline=True)
    stats_embed.add_field(name="Draws", value=f"{total_draws}", inline=True)
    stats_embed.add_field(name="Losses", value=f"{total_losses}", inline=True)
    stats_embed.add_field(name="Total matches", value=f"{total}")

    await ctx.edit_initial_response(embed=stats_embed)


@component.with_slash_command
@tanjun.with_own_permission_check(App.REQUIRED_PERMISSIONS, error_message=App.PERMS_ERR_MSG)
@tanjun.as_slash_command("lb", "leaderboard", default_to_ephemeral=False, always_defer=True)
async def get_leaderboard(ctx: tanjun.abc.Context, bot:hikari.GatewayBot=tanjun.injected(type=hikari.GatewayBot)) -> None:

    DB = Guild_DB(ctx.guild_id)

    def get_leaderboard_for_page(page):

        players_per_page = 20

        place_str_len = 5
        name_len = 21
        elo_str_len = 5

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
            place_str = (str(place) + ".")[:place_str_len]
            displayed_name = (str(player["username"]) + ":")[:name_len]
            displayed_elo = str(round(player["elo"]))[:elo_str_len]
            lb_list +=  place_str.ljust(place_str_len)\
                    +   displayed_name.ljust(name_len)\
                    +   displayed_elo.rjust(elo_str_len) + "\n"
        lb_list += "```"

        lb_embed = hikari.Embed(title="Leaderboard", description=f"Leaderboard page {page + 1}", color=Colors.PRIMARY)
        lb_embed.add_field(name="Rank" + " "*5*2 + "Username" + " "*35*2 + "Score", value=lb_list, inline=False)
        lb_embed.set_footer(text="Don't see yourself? Only players who completed their " + str(Elo.NUM_PLACEMENT_MATCHES) + " placement games are ranked")
        return [lb_embed]

    await create_paginator(ctx, bot, get_leaderboard_for_page, nextlabel="Lower", prevlabel="Higher")


player = tanjun.Component(name="player", strict=True).load_from_scope().make_loader()