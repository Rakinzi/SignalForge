import os
import sys

from diagrams import Cluster, Diagram, Edge
from diagrams.generic.compute import Rack
from diagrams.generic.storage import Storage

sys.path.append(os.path.dirname(__file__))
from diagram_style import EDGE_ATTR, GRAPH_ATTR, NODE_ATTR


def main() -> None:
    with Diagram(
        "Component Architecture",
        direction="LR",
        filename="docs/diagrams/component_architecture",
        outformat="png",
        show=False,
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
        edge_attr=EDGE_ATTR,
    ):
        with Cluster("Data Plane"):
            capture = Rack("Packet Capture")
            flow_norm = Rack("Flow Builder\n(5-tuple)\n+ timeouts")
            capture >> Edge(xlabel="packets", minlen="2") >> flow_norm

        with Cluster("Transport"):
            stream = Storage("Redis Streams")

        with Cluster("Analytics"):
            features = Rack("Feature\nExtraction")
            rules = Rack("Rule Engine")
            stats = Rack("Statistical\nDetection")
            fusion = Rack("Fusion +\nExplainability")
            features >> Edge(xlabel="features", minlen="2") >> rules
            features >> Edge(xlabel="features", minlen="2") >> stats
            rules >> Edge(xlabel="signals", minlen="2") >> fusion
            stats >> Edge(xlabel="signals", minlen="2") >> fusion

        with Cluster("Storage"):
            db = Storage("PostgreSQL")

        with Cluster("API"):
            api = Rack("FastAPI\nREST + SSE")

        with Cluster("UI"):
            ui = Rack("SvelteKit\nDashboard")

        flow_norm >> Edge(xlabel="FlowEnded", minlen="2") >> stream
        stream >> Edge(xlabel="flow summaries", minlen="3", labeldistance="2.2") >> features
        fusion >> Edge(
            xlabel="writes flows, detections, alerts",
            minlen="3",
            labeldistance="1.8",
            labelangle="25",
        ) >> db
        api >> Edge(xlabel="SQL read", minlen="2") >> db
        ui >> Edge(xlabel="queries", minlen="2") >> api
        api >> Edge(
            xlabel="REST + SSE",
            minlen="2",
            labeldistance="3.2",
            labelangle="-30",
        ) >> ui


if __name__ == "__main__":
    main()
