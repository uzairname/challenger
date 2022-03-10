from plugins._utils import *

import asyncio
import hikari
from hikari import Embed


component = tanjun.Component(name="suggestions module")

@component.with_slash_command
@tanjun.with_own_permission_check(
    hikari.Permissions.SEND_MESSAGES
    | hikari.Permissions.VIEW_CHANNEL
    | hikari.Permissions.EMBED_LINKS
    | hikari.Permissions.ADD_REACTIONS
)
@tanjun.with_str_slash_option("suggestion", "a suggestion")
@tanjun.as_slash_command("suggest", "make a suggestion!")
async def suggest_command(ctx: tanjun.abc.Context, *, suggestion: str) -> None:
    react_emojis = ["✅", "❌"]
    embed = Embed(
        color=0xF1C40F,
    )
    embed.add_field(name="Suggestion", value=suggestion)
    embed.set_author(name=f"Suggestion by {ctx.author}", icon=ctx.author.avatar_url)
    msg = await ctx.respond(embed=embed, ensure_result=True)
    for emoji in react_emojis:
        await msg.add_reaction(emoji)


@component.with_slash_command
@tanjun.with_str_slash_option("message_id", "Message ID of the suggestion")
@tanjun.as_slash_command("approve", "approve a suggestion!")
@check_errors
async def approve_command(ctx: tanjun.abc.Context, message_id: str) -> None:
    channel = await ctx.fetch_channel()
    msg = await ctx.rest.fetch_message(channel, int(message_id))

    if not msg.embeds:
        return
    embed = msg.embeds[0]
    embed.set_footer(text=f"Approved by {ctx.author}")
    embed.color = hikari.Color(0x00FF00)
    await msg.edit(embed=embed)
    await msg.remove_all_reactions()
    response = await ctx.respond("Done :ok_hand:", ensure_result=True)
    await asyncio.sleep(3)
    await response.delete()


@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())