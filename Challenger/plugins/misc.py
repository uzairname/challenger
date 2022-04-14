import tanjun


component = tanjun.Component(name="misc module")

@tanjun.as_loader
def load(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())