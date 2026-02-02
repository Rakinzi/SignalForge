#!/usr/bin/env python
"""
Generate Data Flow Diagram (DFD) Level 0 for SignalForge Platform.
Uses proper DFD notation following Yourdon/DeMarco style:
- Circles (ellipse) = Processes
- Rectangles (box) = External Entities
- Open-ended rectangles (cylinder) = Data Stores
- Arrows = Data Flows
"""
import os
import sys

from diagrams import Diagram, Edge, Node

sys.path.append(os.path.dirname(__file__))
from diagram_style import EDGE_ATTR, GRAPH_ATTR, NODE_ATTR


def main() -> None:
    # DFD-compliant node styles
    def process(label: str, num: str = "") -> Node:
        """Process bubble (circle with number)"""
        display_label = f"{num}\n{label}" if num else label
        return Node(
            display_label,
            shape="ellipse",
            style="filled",
            fillcolor="#E3F2FD",
            width="1.8",
            height="1.8",
            fixedsize="true"
        )

    def external_entity(label: str) -> Node:
        """External entity (square box)"""
        return Node(
            label,
            shape="box",
            style="filled",
            fillcolor="#F1F8E9",
            width="1.5",
            height="0.8"
        )

    def datastore(label: str, num: str = "") -> Node:
        """Data store (parallel lines)"""
        display_label = f"D{num}  {label}" if num else label
        return Node(
            display_label,
            shape="folder",
            style="filled",
            fillcolor="#FFF3E0",
            width="2.0",
            height="0.6"
        )

    # Enhanced graph attributes for better layout
    dfd_graph_attr = {
        **GRAPH_ATTR,
        "rankdir": "TB",  # Top to Bottom for better vertical layout
        "ranksep": "1.0",
        "nodesep": "0.8",
        "dpi": "300",  # High-resolution output
        "bgcolor": "white",
    }

    dfd_edge_attr = {
        **EDGE_ATTR,
        "fontsize": "10",
        "labeldistance": "2.0",
        "minlen": "2",
    }

    with Diagram(
        "SignalForge Data Flow Diagram (Level 0)",
        direction="LR",
        filename="docs/diagrams/data_flow",
        outformat="png",
        show=False,
        graph_attr=dfd_graph_attr,
        node_attr=NODE_ATTR,
        edge_attr=dfd_edge_attr,
    ):
        # External entities
        network = external_entity("Network\nTraffic")
        operator = external_entity("Security\nOperator")

        # Processes (numbered 1-4)
        p1_collect = process("Packet\nCapture", "1")
        p2_detect = process("Anomaly\nDetection", "2")
        p3_api = process("Query\nProcessing", "3")

        # Data stores
        d1_streams = datastore("Flow Streams", "1")
        d2_database = datastore("Detection DB", "2")

        # Data flows - Ingest path
        network >> Edge(label="Raw Packets") >> p1_collect
        p1_collect >> Edge(label="Flow Summaries") >> d1_streams
        d1_streams >> Edge(label="Flow Data") >> p2_detect
        p2_detect >> Edge(label="Alerts + Baselines") >> d2_database

        # Data flows - Query path
        operator >> Edge(label="Queries") >> p3_api
        p3_api >> Edge(label="SQL Reads") >> d2_database
        d2_database >> Edge(label="Query Results") >> p3_api
        p3_api >> Edge(label="JSON/SSE") >> operator


if __name__ == "__main__":
    main()
