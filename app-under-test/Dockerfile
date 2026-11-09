# ==============================================================================
# OmniSight Mock Target Application Dockerfile
# Mock e-commerce storefront container with seeded visual anomalies
# ==============================================================================

# Stage 1: Build Application Assets
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . ./
RUN npm run build

# Stage 2: Production Static File Server
FROM node:20-alpine AS runner

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:5173/ || exit 1

CMD ["serve", "-s", "dist", "-l", "5173"]
