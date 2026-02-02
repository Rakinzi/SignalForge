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
        "Threat Boundaries",
        direction="LR",
        filename="docs/diagrams/threat_boundaries",
        outformat="png",
        show=False,
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
    ):
        with Cluster("Untrusted Zone"):
            internet = Switch("Internet")
            attacker = User("Adversary")

        with Cluster("Edge / DMZ"):
            edge = Firewall("Nginx Edge")

        with Cluster("Internal Services"):
            api = Rack("API")
            ui = Rack("UI")
            collector = Rack("Collector")
            detector = Rack("Detector")
            redis = Storage("Redis Streams")

        with Cluster("Data Zone"):
            db = Storage("PostgreSQL")

        internet >> Edge(xlabel="web traffic", minlen="2") >> edge
        attacker >> Edge(xlabel="hostile traffic", minlen="2") >> edge
        edge >> Edge(xlabel="/ui", minlen="2") >> ui
        edge >> Edge(xlabel="/api", minlen="2") >> api
        collector >> Edge(xlabel="FlowEnded", minlen="2") >> redis
        redis >> Edge(xlabel="flow summaries", minlen="2") >> detector
        detector >> Edge(xlabel="writes", minlen="2") >> db
        api >> Edge(xlabel="SQL read", minlen="2") >> db


if __name__ == "__main__":
    main()
