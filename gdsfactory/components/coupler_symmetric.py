from __future__ import annotations

import gdsfactory as gf
from gdsfactory.component import Component
from gdsfactory.components.bend_s import bend_s
from gdsfactory.typings import ComponentSpec, CrossSectionSpec


@gf.cell
def coupler_symmetric(
    bend: ComponentSpec = bend_s,
    gap: float = 0.234,
    dy: float = 4.0,
    dx: float = 10.0,
    cross_section: CrossSectionSpec = "strip",
) -> Component:
    r"""Two coupled straights with bends.

    Args:
        bend: bend spec.
        gap: in um.
        dy: port to port vertical spacing.
        dx: bend length in x direction.
        cross_section: section.

    .. code::

                       dx
                    |-----|
                       ___ o3
                      /       |
             o2 _____/        |
                              |
             o1 _____         |  dy
                     \        |
                      \___    |
                           o4

    """
    c = Component()
    x = gf.get_cross_section(cross_section)
    width = x.width
    dy = (dy - gap - width) / 2

    bend_component = gf.get_component(
        bend,
        size=(dx, dy),
        cross_section=cross_section,
    )

    gap = gap / c.kcl.dbu
    w = bend_component.ports["o1"].width
    y = int(w + gap) // 2

    top_bend = c << bend_component
    bot_bend = c << bend_component

    bot_bend.mirror_y()
    top_bend.movey(+y)
    bot_bend.movey(-y)

    c.add_port("o1", port=bot_bend.ports["o1"])
    c.add_port("o2", port=top_bend.ports["o1"])

    c.add_port("o3", port=top_bend.ports["o2"])
    c.add_port("o4", port=bot_bend.ports["o2"])

    c.info["length"] = bend_component.info["length"]
    c.info["min_bend_radius"] = bend_component.info["min_bend_radius"]
    return c


if __name__ == "__main__":
    c = coupler_symmetric(gap=0.2)
    c.show()
    # c.pprint()

    # for dyi in [2, 3, 4, 5]:
    #     c = coupler_symmetric(gap=0.2, width=0.5, dy=dyi, dx=10.0, layer=(2, 0))
    #     print(f"dy={dyi}, min_bend_radius = {c.info['min_bend_radius']}")
