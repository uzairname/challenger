import tanjun

nl = "\n"

component = tanjun.Component()


@component.with_slash_command
@tanjun.as_slash_command("whats-my-id", "Find out what your User ID is!", default_to_ephemeral=True)
async def whats_my_id(ctx: tanjun.abc.Context) -> None:
    await ctx.respond(f"Hi {ctx.author.mention}! {nl} Your User ID is: ```{ctx.author.id}```")


@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())
