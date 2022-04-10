import functools
import logging
import hikari
import tanjun

from database import Database
from __main__ import bot as bot_instance
from config import Config

import typing

import math
import numpy as np
import pandas as pd
import re
import sympy as sp


class Colors:
    PRIMARY = "37dedb"
    NEUTRAL = "a5a5a5"
    CONFIRM = "ffe373"
    SUCCESS = "#5dde07"
    ERROR = "#ff0000"
    CANCEL = "#ff5500"

DEFAULT_TIMEOUT = 120

class results:
    PLAYER_1 = "player 1"
    PLAYER_2 = "player 2"
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    CANCEL = "cancelled"
    UNDECIDED = "undecided"

class declares:
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    CANCEL = "cancel"

class status:
    NONE = 0
    STAFF = 1

class Embed_Type:
    ERROR = 1
    CONFIRM = 2
    CANCEL = 3
    INFO = 4

class Custom_Embed(hikari.Embed):

    def __init__(self, type, title=None, description=None, url=None, color=None, colour=None, timestamp=None):
        if type == Embed_Type.ERROR:
            super().__init__(color=color or Colors.ERROR, title=title or "Error", description=description or "Error.", url=url, timestamp=timestamp)
        elif type == Embed_Type.CONFIRM:
            super().__init__(color=color or Colors.SUCCESS, title=title or "Confirmed", description=description or "Confirmed.", url=url, timestamp=timestamp)
        elif type == Embed_Type.CANCEL:
            super().__init__(color=color or Colors.NEUTRAL, title=title or "Cancelled", description=description or "Cancelled.", url=url, timestamp=timestamp)
        elif type == Embed_Type.INFO:
            super().__init__(color=color or Colors.PRIMARY, title=title or "Info", description=description, url=url, timestamp=timestamp)


def check_errors(func):
    # for commands that take a context, respond with an error if it doesn't work
    @functools.wraps(func)
    async def wrapper_check_errors(ctx: tanjun.abc.Context, *args, **kwargs):
        try:
            await func(ctx, *args, **kwargs)
        except BaseException:
            await ctx.respond("didnt work :(", ensure_result=True)
            logging.info("command failed: " + str(kwargs.values()))
    return wrapper_check_errors


def construct_df(rows, columns, index_column: str = None):
    df = pd.DataFrame(rows, columns=columns)
    if index_column:
        df.set_index(df[index_column], inplace=True)
    return df

def replace_row_if_col_matches(df:pd.DataFrame, row:pd.Series, column:str):

    drop_index = df.loc[df[column] == row[column]].index
    new_df = pd.concat([df.drop(drop_index), pd.DataFrame(row).T])

    return new_df



class InputParams():
    def __init__(self, input_string):
        text_pat = r"[a-zA-Z\d\s]+"

        channel_pat = r"<#(\d{17,19})>"
        role_pat = r"<@&(\d{17,19})>"
        user_pat = r"<@!?(\d{17,19})>"

        name = re.match(text_pat, input_string)
        if name:
            name = name[0].strip()

        self.channels = np.array(re.findall(channel_pat, input_string)).astype("int64")
        self.roles = np.array(re.findall(role_pat, input_string)).astype("int64")
        self.users = np.array(re.findall(user_pat, input_string)).astype("int64")
        self.text = name


    def describe(self):

        description = ""
        if self.text:
            description += "\nName:\n> " + str(self.text)

        if self.channels.size > 0:
            description += "\nSelected channels:"
            for i in self.channels:
                description += "\n> <#" + str(i) + ">"

        if self.roles.size > 0:
            description += "\nSelected roles:"
            for i in self.roles:
                description += "\n> <@&" + str(i) + ">"

        if self.users.size > 0:
            description += "\nSelected users:"
            for i in self.users:
                description += "\n> <@" + str(i) + ">"

        description += "\n"
        return description


def ensure_registered(func):
    @functools.wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        DB = Database(ctx.guild_id)

        player = DB.get_players(user_id=ctx.author.id)
        if player.empty:
            await ctx.respond(f"Hi {ctx.author.mention}! Please register with /register to play", user_mentions=True)
            return

        return await func(ctx=ctx, *args, **kwargs)

    return wrapper


def check_for_queue(func) -> typing.Callable:

    @functools.wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        DB = Database(ctx.guild_id)

        queues = DB.get_queues(ctx.channel_id)
        if queues.empty:
            await ctx.edit_initial_response("This channel doesn't have a lobby")
            return

        return await func(ctx=ctx, queue=queues.iloc[0], *args, **kwargs)

    return wrapper


def ensure_staff(func):
    @functools.wraps(func)
    async def wrapper(ctx, *args, **kwargs):

        async def is_staff():
            if ctx.author.id == Config.owner_id:
                return True

            DB = Database(ctx.guild_id)

            staff_role = DB.get_config()["staff_role"]

            if staff_role is None:
                guild = await ctx.fetch_guild()

                roles = ctx.member.role_ids
                role_mapping = {}
                for role_id in roles:
                    role_mapping[role_id] = guild.get_role(role_id)

                user_perms = tanjun.utilities.calculate_permissions(member=ctx.member, guild=guild, roles=role_mapping)
                if user_perms & hikari.Permissions.MANAGE_GUILD:
                    return True
                return False

            return bool(staff_role in ctx.member.role_ids)

        if not await is_staff():
            await ctx.respond("Missing permissions")
            return

        return await func(ctx=ctx, *args, **kwargs)

    return wrapper


def take_input(input_instructions:typing.Callable):

    """
    Calls function with input to the slash command.
    params:
        decorated function: slash command function called when confirm button is pressed. function that takes in a hikari.ComponentInteraction event and/or additional kwargs and returns an embed to show when the command is executed.
        input_instructions: function that takes in a tanjun.abc.Context, Database, and/or additional kwargs and returns an embed to show before user confirms their input
    """

    def decorator_take_input(func):
        @functools.wraps(func)
        async def wrapper_take_input(ctx, **kwargs):

            confirm_cancel_row = ctx.rest.build_action_row()
            confirm_cancel_row.add_button(hikari.messages.ButtonStyle.SUCCESS, "Confirm").set_label("Confirm").set_emoji("✔️").add_to_container()
            confirm_cancel_row.add_button(hikari.messages.ButtonStyle.DANGER, "Cancel").set_label("Cancel").set_emoji("❌").add_to_container()

            instructions_embed = await input_instructions(ctx=ctx, **kwargs)
            response = await ctx.respond(embeds=[instructions_embed], components=[confirm_cancel_row], ensure_result=True)

            confirm_embed = Custom_Embed(type=Embed_Type.INFO, title="Confirm?", description="Nothing selected")
            with bot_instance.stream(hikari.InteractionCreateEvent, timeout=DEFAULT_TIMEOUT).filter(
                ("interaction.type", hikari.interactions.InteractionType.MESSAGE_COMPONENT),
                ("interaction.user.id", ctx.author.id),
                ("interaction.message.id", response.id)
            ) as stream:
                async for event in stream:
                    await event.interaction.create_initial_response(hikari.ResponseType.DEFERRED_MESSAGE_UPDATE)
                    if event.interaction.custom_id == "Confirm":
                        confirm_embed = await func(event=event, ctx=ctx, **kwargs)
                        break
                    elif event.interaction.custom_id == "Cancel":
                        confirm_embed = Custom_Embed(type=Embed_Type.CANCEL)
                        break
                    else:
                        confirm_embed = Custom_Embed(type=Embed_Type.ERROR, description="Invalid action.")

            await ctx.edit_initial_response(embeds=[instructions_embed, confirm_embed], components=[])

        return wrapper_take_input
    return decorator_take_input