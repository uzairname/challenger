import hikari
from hikari import Embed
from hikari import InteractionCreateEvent
from hikari.interactions.base_interactions import ResponseType
from hikari.messages import ButtonStyle

import asyncio
import tanjun
from tanjun.abc import SlashContext


embed = tanjun.slash_command_group("embed", "Work with Embeds!", default_to_ephemeral=False)


async def wait(ctx: tanjun.abc.Context):
    await asyncio.sleep(5)
    await ctx.respond("Removed")


@tanjun.as_slash_command("enter", "enter", always_defer=True)
async def enter(ctx:tanjun.abc.Context):
    message = await ctx.fetch_initial_response()

    for i in asyncio.all_tasks():
        if i.get_name() == str(ctx.author.id):
            print(i)
            i.cancel()
            break

    asyncio.create_task(wait(ctx), name=str(ctx.author.id) + "joined_q")
    await ctx.edit_initial_response(content="Waiting...", components=[])






@embed.with_command
@tanjun.as_slash_command("interactive-post", f"Build an Embed!")
async def interactive_post(
    ctx: SlashContext,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
    client: tanjun.Client = tanjun.injected(type=tanjun.Client)
) -> None:
    client.metadata['embed'] = hikari.Embed(title="New Embed")
    row = ctx.rest.build_action_row()
    (
        row.add_button(ButtonStyle.PRIMARY, "📋")
        .set_label("Change Title")
        .set_emoji("📋")
        .add_to_container()
    )
    (
        row.add_button(ButtonStyle.DANGER, "❌")
        .set_label("Exit")
        .set_emoji("❌")
        .add_to_container()
    )
    await ctx.edit_initial_response("Click/Tap your choice below, then watch the embed update!", embed=client.metadata['embed'], components=[row, ])
    try:
        with bot.stream(InteractionCreateEvent, timeout=60).filter(('interaction.user.id', ctx.author.id)) as stream:
            async for event in stream:
                await event.interaction.create_initial_response(
                    ResponseType.DEFERRED_MESSAGE_UPDATE,
                )
                key = event.interaction.custom_id
                if key == "❌":
                    await ctx.edit_initial_response(content=f"Exiting!", components=[])
                    return
                elif key == "📋":
                    await title(ctx, bot, client)

                await ctx.edit_initial_response("Click/Tap your choice below, then watch the embed update!", embed=client.metadata['embed'], components=[row])
    except asyncio.TimeoutError:
        await ctx.edit_initial_response("Waited for 60 seconds... Timeout.", embed=None, components=[])


async def title(ctx: SlashContext, bot: hikari.GatewayBot, client: tanjun.Client):
    embed_dict, *_ = bot.entity_factory.serialize_embed(client.metadata['embed'])
    await ctx.edit_initial_response(content="Set Title for embed:", components=[])
    try:
        with bot.stream(hikari.GuildMessageCreateEvent, timeout=60).filter(('author', ctx.author)) as stream:
            async for event in stream:
                embed_dict['title'] = event.content[:200]
                client.metadata['embed'] = bot.entity_factory.deserialize_embed(embed_dict)
                await ctx.edit_initial_response(content="Title updated!", embed=client.metadata['embed'], components=[])
                await event.message.delete()
                return
    except asyncio.TimeoutError:
        await ctx.edit_initial_response("Waited for 60 seconds... Timeout.", embed=None, components=[])








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



@tanjun.with_str_slash_option("message_id", "Message ID of the suggestion")
@tanjun.as_slash_command("approve", "approve a suggestion!")
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


demo = tanjun.Component(name="demo", strict=True).load_from_scope().make_loader()