"""Routing bundle requires end ports to be on the same orientation but input can be any orientation."""

from __future__ import annotations

import gdsfactory as gf

if __name__ == "__main__":
    c = gf.Component("sample_bundle_impossible")

    top = c << gf.components.nxn(north=8, south=0, east=0, west=0)
    bot = c << gf.components.nxn(north=2, south=2, east=2, west=2)

    top.dmovey(100)

    routes = gf.routing.route_bundle(
        c,
        ports1=bot.ports,
        ports2=top.ports,
        radius=5,
        sort_ports=True,  # switch this to False to see the error
    )

    c.show()
