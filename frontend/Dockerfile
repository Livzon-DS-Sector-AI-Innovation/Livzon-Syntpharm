# Multi-stage Dockerfile for frontend
# Stages: base → dev/builder → runtime

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: base — shared foundation
# ─────────────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS base

WORKDIR /app

# Use Chinese npm mirror for faster downloads
RUN npm config set registry https://registry.npmmirror.com

# Install pnpm globally via npm (bypasses corepack download issues)
RUN npm install -g pnpm@10.33.0

# Copy dependency files
COPY package.json pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: dev — development stage with hot reload
# ─────────────────────────────────────────────────────────────────────────────
FROM base AS dev

# Copy source code
COPY . .

EXPOSE 3000

CMD ["pnpm", "dev"]

# ─────────────────────────────────────────────────────────────────────────────
# Stage 3: builder — production build stage
# ─────────────────────────────────────────────────────────────────────────────
FROM base AS builder

# Copy source code
COPY . .

# Set production environment variables
ENV API_BASE_URL=http://backend:8000
ENV NODE_ENV=production

# Clean and build
RUN rm -rf .next tsconfig.tsbuildinfo
RUN pnpm build

# ─────────────────────────────────────────────────────────────────────────────
# Stage 4: runtime — production runtime (minimal image)
# ─────────────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME="0.0.0.0"
ENV PORT=3000

# Copy only the standalone output from builder
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
