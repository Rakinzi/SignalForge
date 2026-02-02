# Build stage - use Node.js for better SvelteKit compatibility
FROM node:20-alpine AS builder

WORKDIR /app

# Build-time API base URL
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

# Copy package files
COPY package.json bun.lock ./

# Install dependencies with npm (more compatible with SvelteKit adapters)
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

RUN apk add --no-cache curl

# Copy built assets from builder (SvelteKit outputs to build/)
COPY --from=builder /app/build ./build
COPY --from=builder /app/package.json ./

# Install production dependencies only
RUN npm install --production

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -fsS http://localhost:3000 || exit 1

# Set environment
ENV NODE_ENV=production
ENV PORT=3000
ENV HOST=0.0.0.0

# Run the app (SvelteKit node adapter entry point)
CMD ["node", "build/index.js"]
