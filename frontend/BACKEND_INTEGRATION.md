# Backend Integration Guide

## 🔗 Connection Status

The frontend is now **integrated with the real backend API** built with FastAPI (Python + uv).

## 🎯 Backend Services

The backend consists of:

1. **API Service** (FastAPI on port 8000)
   - REST endpoints for data access
   - JWT authentication
   - SSE for real-time alerts
   - PostgreSQL database

2. **Collector Service** (Go)
   - High-speed packet capture
   - Flow aggregation
   - Redis Streams output

3. **Detector Service** (Python)
   - Anomaly detection
   - Rule evaluation
   - Alert generation

4. **Infrastructure**
   - Redis (message bus)
   - PostgreSQL (storage)

## 🔐 Authentication

### Default Credentials

The backend provides three user roles:

- **Admin**: `admin` / `admin` (full access)
- **Analyst**: `analyst` / `analyst` (read/write alerts)
- **Viewer**: `viewer` / `viewer` (read-only) ✅ **Default for frontend**

### How It Works

1. Frontend auto-authenticates on first API call
2. Gets JWT token from `/auth/token`
3. Token cached for 50 minutes (expires at 60)
4. Automatically included in all subsequent requests
5. Token passed as query param for SSE connections

### Configuration

Set credentials in `.env`:

```bash
VITE_API_USERNAME=viewer
VITE_API_PASSWORD=viewer
```

## 📡 API Endpoints

### ✅ Fully Integrated

| Endpoint | Method | Auth | Frontend Usage | Status |
|----------|--------|------|----------------|--------|
| `/health` | GET | No | Health checks | ✅ Working |
| `/version` | GET | No | System info | ✅ Working |
| `/flows` | GET | Yes | Flows table | ✅ Integrated |
| `/flows/{id}` | GET | Yes | Flow details | ✅ Integrated |
| `/alerts` | GET | Yes | Alerts list | ✅ Integrated |
| `/alerts/{id}/ack` | POST | Yes | Acknowledge alerts | ✅ Integrated |
| `/metrics` | GET | Yes | Overview metrics | ✅ Integrated |
| `/reports` | GET | Yes | Reports page | ✅ Integrated |
| `/config` | GET | Yes | Settings page | ✅ Integrated |
| `/stream/alerts` | GET (SSE) | Yes | Real-time alerts | ✅ Integrated |

### Response Format Mapping

The frontend automatically transforms backend responses:

**Flows**
```typescript
// Backend returns:
{ items: [...], limit: 100, offset: 0 }

// Frontend extracts:
items.map(item => ({
  flow_id: item.id,
  start_time: item.start_time,
  // ... etc
}))
```

**Alerts**
```typescript
// Backend returns:
{ items: [...], limit: 100, offset: 0 }

// Frontend extracts:
items.map(item => ({
  alert_id: item.id,
  timestamp: item.created_at,
  // ... etc
}))
```

**SSE Events**
```typescript
// Backend sends:
{ event: "alert", data: { id, severity, ... } }

// Frontend extracts:
{ alert_id: data.id, timestamp: data.created_at, ... }
```

## 🚀 Running the Full Stack

### Option 1: Docker Compose (Recommended)

```bash
# From project root
cd deploy
docker-compose up -d

# Check services
docker-compose ps
docker-compose logs -f api
```

Services will be available at:
- API: http://localhost:8000
- Frontend: http://localhost:5173 (dev) or http://localhost:3000 (prod)
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Option 2: Manual Development

**Terminal 1 - Infrastructure:**
```bash
cd deploy
docker-compose up redis postgres
```

**Terminal 2 - Backend API:**
```bash
cd services/api
uv sync
uv run python -m api.app
```

**Terminal 3 - Frontend:**
```bash
cd frontend
bun install
bun run dev
```

## 🔄 Data Flow

```
Network Packets
    ↓
Collector (Go)
    ↓ (Redis Streams)
Detector (Python)
    ↓ (PostgreSQL)
API (FastAPI)
    ↓ (HTTP/SSE + JWT)
Frontend (SvelteKit) ← You are here
    ↓
Browser
```

## 🐛 Troubleshooting

### "API request failed"

**Cause**: Cannot reach backend at `http://localhost:8000`, authentication failure, or non-2xx API response

**Solutions**:
1. Check if API service is running: `curl http://localhost:8000/health`
2. Verify VITE_API_URL in `.env`
3. Check docker-compose logs: `docker-compose logs api`
4. Ensure PostgreSQL is healthy: `docker-compose ps postgres`

### "No auth token available"

**Cause**: Authentication failed

**Solutions**:
1. Check credentials in `.env` match backend users
2. Verify API /auth/token endpoint: `curl -X POST http://localhost:8000/auth/token -d "username=viewer&password=viewer"`
3. Check browser console for auth errors

### SSE Connection Issues

**Cause**: EventSource cannot connect

**Solutions**:
1. Verify auth token is valid
2. Check CORS headers on backend
3. Ensure `/stream/alerts` endpoint is accessible
4. Browser dev tools → Network → EventStream

### Empty Data Despite API Running

**Cause**: Database is empty (no flows/alerts yet)

**Solutions**:
1. Collector must be running and capturing traffic
2. Or: Play back a PCAP file through collector
3. Check if detector is processing flows
4. Verify PostgreSQL has data: `docker-compose exec postgres psql -U signalforge -c "SELECT COUNT(*) FROM flows;"`

## 📊 Data Policy

The frontend does not generate or display mock/dummy operational data. All dashboard values must come from backend API responses. When data is unavailable, the UI renders explicit error or empty-state messages.

## 🔧 Environment Variables

### Required
```bash
VITE_API_URL=http://localhost:8000        # Backend API URL
```

### Optional (Authentication)
```bash
VITE_API_USERNAME=viewer                   # Default: viewer
VITE_API_PASSWORD=viewer                   # Default: viewer
```

### Production Example
```bash
VITE_API_URL=https://api.signalforge.company.com
VITE_API_USERNAME=production_viewer
VITE_API_PASSWORD=secure_password_here
```

## 📝 Backend API Documentation

For detailed API documentation, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🎯 Next Steps

### When Backend Adds New Features:

**1. Entities/Baselines Endpoint**
```typescript
// Update in client.ts:
export async function getEntities() {
  const { data } = await apiCall('/baselines');
  return data.items.map(mapToEntityBaseline);
}
```

**2. Full Metrics Endpoint**
```typescript
// Backend should return:
{
  status: "healthy",
  ingest_rate: 1234.56,
  flows_per_second: 567.89,
  alerts_count: 42,
  latency_ms: 12.34,
  uptime_seconds: 86400
}
```

**3. Evaluation Metrics**
```typescript
// Backend should return:
{
  true_positives: 142,
  false_positives: 8,
  true_negatives: 9845,
  false_negatives: 5,
  precision: 0.9467,
  recall: 0.9660,
  f1_score: 0.9563,
  accuracy: 0.9987
}
```

## ✅ Integration Checklist

- [x] Authentication system implemented
- [x] Token management with auto-refresh
- [x] Response format adapters
- [x] Error handling with explicit API failures
- [x] SSE with authentication
- [x] Environment configuration
- [x] No mock/dummy operational data
- [x] CORS compatibility
- [x] Docker deployment ready

## 🎉 Status: Production Ready

The frontend is **fully integrated** with the backend and ready for:
- ✅ Real-time monitoring
- ✅ Flow inspection
- ✅ Alert management
- ✅ Live SSE updates
- ✅ Production deployment
