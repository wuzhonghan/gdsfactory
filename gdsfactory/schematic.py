import json
from typing import Any

from omegaconf import OmegaConf
from pydantic import BaseModel, Field, model_validator

from gdsfactory.config import PATH
from gdsfactory.typings import Anchor, Component


class Instance(BaseModel):
    component: str
    settings: dict[str, Any] = Field(default_factory=dict)
    info: dict[str, Any] = Field(default_factory=dict, exclude=True)
    na: int | None = None
    nb: int | None = None
    dax: float | None = None
    day: float | None = None
    dbx: float | None = None
    dby: float | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="before")
    @classmethod
    def update_settings_and_info(cls, values):
        """Validator to update component, settings and info based on the component."""
        component = values.get("component")
        settings = values.get("settings", {})
        info = values.get("info", {})

        import gdsfactory as gf

        c = gf.get_component(component)
        component_info = c.info.model_dump(exclude_none=True)
        component_settings = c.settings.model_dump(exclude_none=True)
        values["info"] = {**component_info, **info}
        values["settings"] = {**component_settings, **settings}
        values["component"] = c.function_name
        return values


class Placement(BaseModel):
    x: str | float = 0
    y: str | float = 0
    xmin: str | float | None = None
    ymin: str | float | None = None
    xmax: str | float | None = None
    ymax: str | float | None = None
    dx: float = 0
    dy: float = 0
    port: str | Anchor | None = None
    rotation: float = 0
    mirror: bool | str | float = False

    def __getitem__(self, key: str) -> Any:
        """Allows to access the placement attributes as a dictionary."""
        return getattr(self, key, 0)

    model_config = {"extra": "forbid"}


class Bundle(BaseModel):
    links: dict[str, str]
    settings: dict[str, Any] = Field(default_factory=dict)
    routing_strategy: str = "route_bundle"

    model_config = {"extra": "forbid"}


class Netlist(BaseModel):
    """Netlist defined component.

    Parameters:
        instances: dict of instances (name, settings, component).
        placements: dict of placements.
        connections: dict of connections.
        routes: dict of routes.
        name: component name.
        info: information (polarization, wavelength ...).
        ports: exposed component ports.
        settings: input variables.
    """

    pdk: str = ""
    instances: dict[str, Instance] = Field(default_factory=dict)
    placements: dict[str, Placement] = Field(default_factory=dict)
    connections: dict[str, str] = Field(default_factory=dict)
    routes: dict[str, Bundle] = Field(default_factory=dict)
    name: str | None = None
    info: dict[str, Any] = Field(default_factory=dict)
    ports: dict[str, str] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict, exclude=True)

    model_config = {"extra": "forbid"}


_route_counter = 0


class Net(BaseModel):
    """Net between two ports.

    Parameters:
        ip1: instance_name,port 1.
        ip2: instance_name,port 2.
        name: route name.
    """

    ip1: str
    ip2: str
    settings: dict[str, Any] = Field(default_factory=dict)
    name: str | None = None

    def __init__(self, **data):
        """Initialize the net."""
        global _route_counter
        super().__init__(**data)
        # If route name is not provided, generate one automatically
        if self.name is None:
            self.name = f"route_{_route_counter}"
            _route_counter += 1


class Link(BaseModel):
    """Link between instances.

    Parameters:
        instance1: instance name 1.
        instance2: instance name 2.
        port1: port name 1.
        port2: port name 2.
    """

    instance1: str
    instance2: str
    port1: str
    port2: str


class Schematic(BaseModel):
    """Schematic."""

    netlist: Netlist = Field(default_factory=Netlist)
    nets: list[Net] = Field(default_factory=list)
    placements: dict[str, Placement] = Field(default_factory=dict)
    links: list[Link] = Field(default_factory=list)

    def add_instance(
        self, name: str, instance: Instance, placement: Placement | None = None
    ) -> None:
        self.netlist.instances[name] = instance
        if placement:
            self.add_placement(name, placement)

    def add_placement(
        self,
        instance_name: str,
        placement: Placement,
    ) -> None:
        """Add placement to the netlist.

        Args:
            instance_name: instance name.
            placement: placement.
        """
        self.placements[instance_name] = placement
        self.netlist.placements[instance_name] = placement

    def from_component(self, component: Component) -> None:
        n = component.get_netlist()
        self.netlist = Netlist.model_validate(n)

    def add_net(self, net: Net) -> None:
        """Add a net between two ports."""
        self.nets.append(net)
        if net.name not in self.netlist.routes:
            self.netlist.routes[net.name] = Bundle(
                links={net.ip1: net.ip2}, settings=net.settings
            )
        else:
            self.netlist.routes[net.name].links[net.ip1] = net.ip2

    def plot_netlist(
        self,
        with_labels: bool = True,
        font_weight: str = "normal",
    ):
        """Plots a netlist graph with networkx.

        Args:
            with_labels: add label to each node.
            font_weight: normal, bold.
        """
        import matplotlib.pyplot as plt
        import networkx as nx

        plt.figure()
        netlist = self.netlist
        connections = netlist.connections
        placements = self.placements or netlist.placements
        G = nx.Graph()
        G.add_edges_from(
            [
                (",".join(k.split(",")[:-1]), ",".join(v.split(",")[:-1]))
                for k, v in connections.items()
            ]
        )
        pos = {k: (v["x"], v["y"]) for k, v in placements.items()}
        labels = {k: ",".join(k.split(",")[:1]) for k in placements.keys()}

        for node, placement in placements.items():
            if not G.has_node(
                node
            ):  # Check if the node is already in the graph (from connections), to avoid duplication.
                G.add_node(node)
                pos[node] = (placement.x, placement.y)

        for net in self.nets:
            G.add_edge(net.ip1.split(",")[0], net.ip2.split(",")[0])

        nx.draw(
            G,
            with_labels=with_labels,
            font_weight=font_weight,
            labels=labels,
            pos=pos,
        )
        return G


def write_schema(
    model: BaseModel = Netlist, schema_path_json=PATH.schema_netlist
) -> None:
    s = model.model_json_schema()
    d = OmegaConf.create(s)

    schema_path_yaml = schema_path_json.with_suffix(".yaml")

    schema_path_yaml.write_text(OmegaConf.to_yaml(d))
    schema_path_json.write_text(json.dumps(OmegaConf.to_container(d)))


if __name__ == "__main__":
    import gdsfactory as gf
    import gdsfactory.schematic as gt

    s = Schematic()
    s.add_instance("mzi1", gt.Instance(component=gf.c.mzi(delta_length=10)))
    s.add_instance("mzi2", gt.Instance(component=gf.c.mzi(delta_length=100)))
    s.add_instance("mzi3", gt.Instance(component=gf.c.mzi(delta_length=200)))
    s.add_placement("mzi1", gt.Placement(x=000))
    s.add_placement("mzi2", gt.Placement(x=100, y=100))
    s.add_placement("mzi3", gt.Placement(x=200))
    s.add_net(gt.Net(ip1="mzi1,o2", ip2="mzi2,o2"))
    s.add_net(gt.Net(ip1="mzi2,o2", ip2="mzi3,o1"))
    g = s.plot_netlist()
