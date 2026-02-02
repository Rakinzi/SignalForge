# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SignalForge Frontend is a real-time network anomaly detection dashboard built with **SvelteKit 2.x (Svelte 5)**, Tailwind CSS v4, and Skeleton UI. It's designed for professional security monitoring with a cyber-themed interface and mobile-responsive design.

**Critical**: This project uses **Svelte 5** with runes (`$state`, `$derived`, `$effect`). Always use the Svelte MCP server tools when working with Svelte code:
- Use `svelte-autofixer` tool on ALL Svelte components before finalizing code
- Use `list-sections` then `get-documentation` for Svelte 5 patterns
- Never use deprecated Svelte 4 patterns like `<svelte:component>`

## Development Commands

```bash
# Development
bun run dev                # Start dev server on http://localhost:5173

# Building
bun run build              # Production build
bun run preview            # Preview production build

# Code Quality
bun run check              # Type check with svelte-check
bun run lint               # Lint with ESLint + Prettier
bun run format             # Format code with Prettier

# Testing
bun run test:unit          # Run Vitest unit tests
bun run test:e2e           # Run Playwright e2e tests
bun run test               # Run all tests
```

**Note**: Use `bun` not `npm` - this is a bun-first project.

## Architecture

### API Client Pattern (Critical)

The API client in `src/lib/api/client.ts` implements **automatic mock data fallback**:

1. **Health Check System**: Checks `/health` endpoint every 30 seconds
2. **Graceful Degradation**: Returns mock data if API unavailable
3. **JWT Authentication**: Automatic token refresh via `src/lib/api/auth.ts`
4. **Response Mapping**: Backend returns `{items: [...]}`, frontend expects arrays

When adding new API endpoints:
```typescript
// Pattern to follow
export async function newEndpoint(): Promise<DataType[]> {
    const { data, usedMock } = await apiCall<BackendResponse>('/endpoint');

    if (usedMock || !data) {
        return generateMockData(); // Always provide mock fallback
    }

    return data.items; // Extract items array from backend response
}
```

### Component Architecture

**Reusable Professional Components** (in `src/lib/components/`):
- `DataTable.svelte` - Full pagination, sorting, responsive (hides page numbers on mobile)
- `FilterBar.svelte` - Consistent filter layout with Apply/Clear buttons
- `FormInput.svelte` / `FormSelect.svelte` - Standardized form controls
- `MetricCard.svelte` - Metric display cards
- `Navbar.svelte` - Top navbar with profile dropdown
- `Sidebar.svelte` - Responsive sidebar with mobile menu support

**Layout System**:
- Fixed navbar at top (64px height)
- Sidebar: Hidden on mobile, slides in with overlay, fixed on desktop (lg+)
- Main content: Full width on mobile, `ml-64` (264px) margin on desktop
- Responsive padding: `p-4` (mobile) → `md:p-6` → `lg:p-8`

### Responsive Design Patterns

**Breakpoints**:
- `sm`: 640px (mobile landscape)
- `md`: 768px (tablets)
- `lg`: 1024px (desktop - sidebar becomes permanent)

**Grid Patterns**:
- Stats cards: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`
- Two-column layouts: `grid-cols-1 md:grid-cols-2`
- Three-column layouts: `grid-cols-1 sm:grid-cols-3`

### SSE (Server-Sent Events) Pattern

Real-time alerts use SSE with JWT token authentication:

```typescript
// Pattern in alerts/+page.svelte
const eventSource = await connectToAlertStream(
    (newAlert) => { /* handle new alert */ },
    () => { /* handle disconnect */ }
);
```

Token is passed as query parameter due to EventSource limitations. Always clean up EventSource in `onDestroy`.

## Styling System

### CSS Variables (in `src/routes/layout.css`)

Cyber-themed color system with dark/light mode:
```css
--accent-primary: #007bff (light) / #00d9ff (dark)
--color-critical: #ff0040
--color-success: #00ff41
--color-medium: #ffaa00
```

All colors support dark mode. Use CSS variables, not hardcoded colors:
```svelte
<!-- Good -->
<div class="text-[var(--text-primary)]">

<!-- Bad -->
<div class="text-gray-800">
```

### Icon System

Use **svelte-hero-icons** (NOT lucide-svelte):
```svelte
<script>
import { Icon } from 'svelte-hero-icons';
</script>

<Icon src="arrow-path" class="w-4 h-4" />
```

Never use emojis for icons - this is a professional enterprise UI.

## Svelte 5 Patterns

### State Management
```svelte
let value = $state(initialValue);           // Reactive state
let derived = $derived(value * 2);          // Derived state
let filtered = $derived(items.filter(...)); // Derived with logic
```

### Effects
```svelte
$effect(() => {
    // Setup
    const interval = setInterval(doSomething, 1000);

    // Cleanup (return function)
    return () => clearInterval(interval);
});
```

### Component Props (Svelte 5)
```svelte
<script lang="ts">
interface Props {
    value: string;
    optional?: boolean;
}

let { value, optional = false }: Props = $props();
</script>
```

### Each Blocks
Always include keys:
```svelte
{#each items as item (item.id)}
    <div>{item.name}</div>
{/each}
```

### No `<svelte:component>`
Deprecated in Svelte 5. Use `{@const}` pattern:
```svelte
{#each navItems as item (item.href)}
    {@const Icon = item.icon}
    <Icon class="w-5 h-5" />
{/each}
```

## Backend Integration

### FastAPI Backend Structure
- **Base URL**: `/api` (production) or `http://localhost:8000` (dev)
- **Authentication**: JWT tokens (60min expiry, refresh at 50min)
- **Response Format**: `{items: [...], limit: N, offset: N}`
- **SSE Endpoint**: `/stream/alerts?token=...`

### Environment Variables
```bash
VITE_API_URL=/api              # API base URL
VITE_API_USERNAME=viewer       # Default auth (development only)
VITE_API_PASSWORD=viewer       # Default auth (development only)
```

## Common Patterns

### Adding a New Page
1. Create `src/routes/pagename/+page.svelte`
2. Add route to `Sidebar.svelte` navItems array
3. Use professional components (DataTable, FilterBar, etc.)
4. Make responsive with proper grid classes
5. Run `svelte-autofixer` before committing

### Adding a New API Endpoint
1. Add TypeScript interface to `src/lib/types.ts`
2. Add function to `src/lib/api/client.ts` with mock fallback
3. Map backend response format (extract `items` array)
4. Add authentication if needed (default: true)

### Responsive Component Checklist
- Mobile menu: Hide sidebar by default, show hamburger button
- Grids: Start with `grid-cols-1`, add breakpoints
- Pagination: Show "Page X of Y" on mobile, full pagination on sm+
- Spacing: Use responsive padding (`p-4 md:p-6 lg:p-8`)

## Docker

```bash
# Build
docker build -t signalforge-ui .

# Run
docker run -p 3000:3000 -e VITE_API_URL=http://api:8000 signalforge-ui
```

Build uses multi-stage with bun and includes `VITE_API_URL` build arg.

## Page-Specific Notes

### Alerts Page (`/alerts`)
- Uses SSE for real-time updates with auto-reconnect
- List-based design (not table) with alert cards
- Stats cards show Active/Acknowledged/Resolved counts
- Acknowledge button only for active alerts

### Flows Page (`/flows`)
- Uses DataTable component with full pagination
- Filter by source/dest IP and protocol
- Column formatters for bytes, duration, time

### Entities Page (`/entities`)
- DataTable with 7 columns (entity_id, type, rates, confidence, last_seen)
- Stats cards show total/IP/service/host counts

### Reports Page (`/reports`)
- Performance metrics: Precision, Recall, F1, Accuracy
- Confusion matrix visualization (cards + table)
- No verbose descriptions (professional/minimal text)

### Settings Page (`/settings`)
- Read-only configuration display
- System info, detector config, architecture overview
- Professional icon usage (no emojis)
