# SignalForge Frontend

Real-time network anomaly detection dashboard built with SvelteKit, Tailwind CSS v4, and Skeleton UI.

## 🎨 Tech Stack

- **Framework**: SvelteKit 2.x (Svelte 5)
- **Build Tool**: Vite 7.x
- **Styling**: Tailwind CSS v4 + Skeleton UI
- **Package Manager**: bun
- **Language**: TypeScript

## 🚀 Features

- **Real-time Monitoring**: Live SSE connection for instant alert updates
- **Explainable Detection**: Every alert shows WHY it was triggered
- **Cyber-themed UI**: Dark/Light mode with neon accents
- **Responsive Design**: Mobile-friendly interface
- **Mock Data Fallback**: Graceful degradation when API is unavailable

## 📦 Installation

### Prerequisites

- [bun](https://bun.sh) v1.2.21 or higher

### Setup

```bash
# Install dependencies
bun install

# Copy environment variables
cp .env.example .env

# Start development server
bun run dev

# Build for production
bun run build

# Preview production build
bun run preview
```

## 🐳 Docker

### Build

```bash
docker build -t signalforge-ui .
```

### Run

```bash
docker run -p 3000:3000 -e VITE_API_URL=http://api:8000 signalforge-ui
```

## 📂 Project Structure

```
frontend/
├── src/
│   ├── lib/
│   │   ├── api/
│   │   │   └── client.ts          # API client with mock fallback
│   │   ├── components/
│   │   │   └── Navigation.svelte   # Main navigation
│   │   └── types.ts                # TypeScript types
│   ├── routes/
│   │   ├── +layout.svelte          # Root layout
│   │   ├── +page.svelte            # Overview page
│   │   ├── flows/                  # Flows page
│   │   ├── alerts/                 # Alerts page (SSE)
│   │   ├── entities/               # Entities page
│   │   ├── reports/                # Reports page
│   │   └── settings/               # Settings page
│   └── app.html                    # HTML template
├── Dockerfile
└── package.json
```

## 🎯 Pages

### Overview (`/`)
- System health status
- Ingest rate metrics
- Flows per second
- Active alerts count
- Processing latency

### Flows (`/flows`)
- Network flow table with filters
- Source/Destination IP filtering
- Protocol filtering
- Flow detail panel with explainability

### Alerts (`/alerts`)
- Real-time alert stream (SSE)
- Severity filtering (Critical, High, Medium, Low, Info)
- Status filtering (Active, Acknowledged, Resolved)
- Acknowledgment workflow

### Entities (`/entities`)
- IP/Service/Host baseline profiles
- Average packet/byte rates
- Connection counts
- Baseline confidence scores

### Reports (`/reports`)
- Confusion matrix visualization
- Precision, Recall, F1 Score, Accuracy
- True/False Positives/Negatives
- Performance metrics

### Settings (`/settings`)
- System configuration (read-only)
- Detector status
- Architecture information
- Privacy notice

## 🎨 Theme

The UI uses a cyber security theme with:

- **Primary Colors**: Cyber blue (#007bff → #00ffff)
- **Neon Accents**: Cyan, Magenta, Green
- **Alert Colors**: Critical (red), High (orange), Medium (yellow), Low (blue)
- **Dark Mode**: Deep navy backgrounds with cyan accents
- **Light Mode**: Clean whites with blue accents

Custom CSS variables are defined in `src/routes/layout.css`.

## 🔌 API Integration

The frontend automatically detects API availability and falls back to mock data when offline.

### API Endpoints

- `GET /health` - System health
- `GET /metrics` - Current metrics
- `GET /flows` - Flow summaries
- `GET /flows/:id` - Flow details
- `GET /alerts` - Alerts list
- `POST /alerts/:id/ack` - Acknowledge alert
- `GET /entities` - Entity baselines
- `GET /reports` - Evaluation metrics
- `GET /config` - System config
- `GET /version` - Version info
- `GET /stream/alerts` - SSE alert stream

### Environment Variables

```bash
VITE_API_URL=http://localhost:8000  # API base URL
```

## 🧪 Testing

```bash
# Run unit tests
bun run test:unit

# Run e2e tests
bun run test:e2e

# Run all tests
bun run test
```

## 🔧 Development

### Code Quality

```bash
# Lint
bun run lint

# Format code
bun run format

# Type check
bun run check
```

## 🚢 Deployment

### Production Build

```bash
bun run build
```

### Adapter

The project uses `@sveltejs/adapter-auto` which automatically selects the appropriate adapter based on your deployment platform.

## 🔒 Security

- No sensitive data stored in frontend
- API calls use standard HTTPS
- No payload inspection (metadata only)
- Privacy-by-design architecture

## 📄 License

Part of the SignalForge platform - Network Anomaly Detection System
