import tanjun

component = tanjun.Component(name="misc module")

misc = tanjun.Component(name="misc", strict=True).load_from_scope().make_loader()