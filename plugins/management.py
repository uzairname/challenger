from plugins.utils import *
from __main__ import DB

component = tanjun.Component(name="management module")



@component.with_slash_command
@tanjun.with_str_slash_option("category", options={"lobby channels", "permissions"})
@tanjun.as_slash_command("config", "settings (admin only)", default_to_ephemeral=True)
def settings(ctx:tanjun.abc.Context):
    pass


@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())