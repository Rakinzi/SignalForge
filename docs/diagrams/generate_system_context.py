import os
import sys

from diagrams import Cluster, Diagram, Edge
from diagrams.generic.compute import Rack
from diagrams.generic.network import Firewall, Switch
from diagrams.generic.storage import Storage
from diagrams.onprem.client import User

sys.path.append(os.path.dirname(__file__))
from diagram_style import EDGE_ATTR, GRAPH_ATTR, NODE_ATTR


def main() -> None:
    with Diagram(
        "System Context",
        direction="LR",
        filename="docs/diagrams/system_context",
        outformat="png",
        show=False,
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
    ):
        internet = Switch("Internet / Network")
        operator = User("SOC Analyst")
        admin = User("Platform Admin")

        with Cluster("SignalForge Platform"):
            edge = Firewall("Nginx Edge")
            ui = Rack("UI\n(SvelteKit)")
            api = Rack("API\n(FastAPI)")
            collector = Rack("Collector\n(Go)")
            detector = Rack("Detector\n(Python)")
            redis = Storage("Redis Streams")
            postgres = Storage("PostgreSQL")

        internet >> Edge(xlabel="packet headers", minlen="2") >> collector
        collector >> Edge(xlabel="FlowEnded", minlen="2") >> redis
        redis >> Edge(xlabel="flow summaries", minlen="2") >> detector
        detector >> Edge(xlabel="writes", minlen="2") >> postgres
        api >> Edge(xlabel="SQL read", minlen="2") >> postgres

        operator >> Edge(xlabel="dashboard", minlen="2") >> edge
        admin >> Edge(xlabel="ops + config", minlen="2") >> edge
        edge >> Edge(xlabel="/ui", minlen="2") >> ui
        edge >> Edge(xlabel="/api", minlen="2") >> api
        ui >> Edge(xlabel="REST + SSE", minlen="2") >> api


if __name__ == "__main__":
    main()
