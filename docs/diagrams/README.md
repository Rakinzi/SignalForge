# SignalForge Diagrams

This directory contains all architectural diagrams for the SignalForge platform.

## Diagram Types

### 1. **Data Flow Diagram (DFD)** - `data_flow.png`
Level 0 DFD showing data movement through the system using Yourdon/DeMarco notation:
- **Circles**: Processes (Packet Capture, Anomaly Detection, Query Processing)
- **Rectangles**: External Entities (Network Traffic, Security Operator)
- **Folders**: Data Stores (Flow Streams, Detection DB)
- **Arrows**: Data Flows with labels

### 2. **Sequence Diagram** - `sequence.png`
UML sequence diagram showing end-to-end message flow:
- Data ingestion pipeline
- Real-time alerting flow
- Operator query interactions
- Alert acknowledgment process

### 3. **System Context** - `system_context.png`
High-level view of the platform within its environment

### 4. **Component Architecture** - `component_architecture.png`
Internal component structure and relationships

### 5. **Deployment Diagram** - `deployment.png`
Docker container deployment architecture

### 6. **Threat Boundaries** - `threat_boundaries.png`
Security trust boundaries and threat surfaces

## Requirements

### Python Dependencies
```bash
pip install diagrams graphviz plantuml requests
```

### System Dependencies
- **Graphviz**: `brew install graphviz` (macOS) or `apt-get install graphviz` (Linux)
- **Java** (optional, for PlantUML jar): For offline PlantUML rendering

## Generating Diagrams

### Generate All Diagrams
```bash
python generate_all.py
```

### Generate Individual Diagrams
```bash
python generate_system_context.py
python generate_component_architecture.py
python generate_dfd.py
python generate_sequence_plantuml.py
python generate_deployment.py
python generate_threat_boundaries.py
```

## Output

All diagrams are generated as high-resolution PNG files (300 DPI) suitable for:
- Documentation (DOCX, PDF)
- Presentations
- Web display
- Print media

## Styling

Diagram styling is centralized in `diagram_style.py`:
- **Graph attributes**: Layout, spacing, DPI
- **Node attributes**: Fonts, sizes
- **Edge attributes**: Colors, arrow styles, label positioning

## PlantUML Sequence Diagram

The sequence diagram uses PlantUML format (`sequence.puml`) for better UML compliance.

The generation script tries multiple methods:
1. Python plantuml package (uses public server)
2. Local plantuml.jar with Java
3. Direct HTTP requests to PlantUML web service

## Integration with Documentation

Diagrams are automatically embedded when generating DOCX documentation:
```bash
cd ../
python generate_docx.py
```

See `../generate_docx.py` for details on converting Markdown to DOCX with diagrams.

## References

- [Python Diagrams Library](https://diagrams.mingrammer.com/)
- [Graphviz Documentation](https://graphviz.org/documentation/)
- [PlantUML Guide](https://plantuml.com/)
- [DFD Best Practices](https://en.wikipedia.org/wiki/Data-flow_diagram)
- [UML Sequence Diagrams](https://www.uml-diagrams.org/sequence-diagrams.html)
