from plugins._utils import *


component = tanjun.Component(name="queue module")



@component.with_slash_command
@tanjun.as_slash_command("join", "join the queue", default_to_ephemeral=True)
async def joinq(ctx: tanjun.abc.Context) -> None:
    await ctx.respond(f"{ctx.author.mention} you have silently joined the queue")


@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())