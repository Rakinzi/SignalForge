# Build stage
FROM oven/bun:1.2.21-alpine AS builder

WORKDIR /app

# Build-time API base URL
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

# Copy package files
COPY package.json bun.lock ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy source code
COPY . .

# Build the application
RUN bun run build

# Production stage
FROM oven/bun:1.2.21-alpine

WORKDIR /app

RUN apk add --no-cache curl

# Copy built assets from builder
COPY --from=builder /app/build ./build
COPY --from=builder /app/package.json ./

# Install production dependencies only
RUN bun install --production --frozen-lockfile

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -fsS http://localhost:3000 || exit 1

# Set environment
ENV NODE_ENV=production
ENV PORT=3000

# Run the app
CMD ["bun", "run", "build/index.js"]
