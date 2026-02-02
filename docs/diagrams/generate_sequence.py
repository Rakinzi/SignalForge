import os
import sys

from diagrams import Cluster, Diagram, Edge, Node

sys.path.append(os.path.dirname(__file__))
from diagram_style import EDGE_ATTR, GRAPH_ATTR, NODE_ATTR


def main() -> None:
    graph_attr = {
        **GRAPH_ATTR,
        "rankdir": "LR",
    }
    def process(label: str) -> Node:
        return Node(label, shape="box", style="rounded,filled", fillcolor="#E7F3FF")

    def external(label: str) -> Node:
        return Node(label, shape="circle", style="filled", fillcolor="#E8F5E9")

    def datastore(label: str) -> Node:
        return Node(label, shape="cylinder", style="filled", fillcolor="#FFF3E0")

    flow_node_attr = {
        **NODE_ATTR,
        "shape": "box",
        "style": "rounded,filled",
        "fillcolor": "#E7F3FF",
    }

    with Diagram(
        "End-to-End Sequence",
        direction="TB",
        filename="docs/diagrams/sequence",
        outformat="png",
        show=False,
        graph_attr=graph_attr,
        node_attr=flow_node_attr,
        edge_attr=EDGE_ATTR,
    ):
        with Cluster("Ingest Path"):
            network = external("Network Packets")
            collector = process("Collector")
            redis = datastore("Redis Streams")
            detector = process("Detector")
            db = datastore("PostgreSQL")

            network >> Edge(xlabel="1. packet headers", minlen="3", labeldistance="1.4", labelangle="-15") >> collector
            collector >> Edge(xlabel="2. FlowEnded", minlen="3", labeldistance="1.4", labelangle="-15") >> redis
            redis >> Edge(xlabel="3. flow summaries", minlen="3", labeldistance="1.4", labelangle="-15") >> detector
            detector >> Edge(xlabel="4. write flows + alerts", minlen="4", labeldistance="1.6", labelangle="-10") >> db

        with Cluster("UI Path"):
            api = process("API")
            ui = external("Operator UI")
            api >> Edge(xlabel="7. REST + SSE", minlen="3", labeldistance="1.4", labelangle="15") >> ui
            ui >> Edge(xlabel="5. queries", minlen="3", labeldistance="1.4", labelangle="-15") >> api
            api >> Edge(xlabel="6. SQL read", minlen="3", labeldistance="1.6", labelangle="25") >> db


if __name__ == "__main__":
    main()
