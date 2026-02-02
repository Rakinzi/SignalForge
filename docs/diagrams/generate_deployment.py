import os
import sys

from diagrams import Cluster, Diagram, Edge
from diagrams.generic.compute import Rack
from diagrams.generic.network import Firewall
from diagrams.generic.storage import Storage
from diagrams.onprem.client import Client

sys.path.append(os.path.dirname(__file__))
from diagram_style import EDGE_ATTR, GRAPH_ATTR, NODE_ATTR


def main() -> None:
    with Diagram(
        "Deployment (Docker Compose)",
        direction="LR",
        filename="docs/diagrams/deployment",
        outformat="png",
        show=False,
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
    ):
        user = Client("Browser")

        with Cluster("Host"):
            with Cluster("Docker Compose Network"):
                edge = Firewall("Nginx\n:8088")
                ui = Rack("UI\n(SvelteKit)")
                api = Rack("API\n(FastAPI)")
                collector = Rack("Collector\n(Go)")
                detector = Rack("Detector\n(Python)")
                redis = Storage("Redis Streams")
                postgres = Storage("PostgreSQL")

        user >> Edge(xlabel="HTTPS", minlen="2") >> edge
        edge >> Edge(xlabel="/ui", minlen="2") >> ui
        edge >> Edge(xlabel="/api", minlen="2") >> api
        collector >> Edge(xlabel="FlowEnded", minlen="2") >> redis
        redis >> Edge(xlabel="flow summaries", minlen="2") >> detector
        detector >> Edge(xlabel="writes", minlen="2") >> postgres
        api >> Edge(xlabel="SQL read", minlen="2") >> postgres
        ui >> Edge(xlabel="REST + SSE", minlen="2") >> api


if __name__ == "__main__":
    main()
