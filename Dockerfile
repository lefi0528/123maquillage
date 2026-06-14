# Stage 1: Build stage
FROM node:22-alpine AS builder
WORKDIR /app

# Install build dependencies for better-sqlite3 native compilation
RUN apk add --no-cache python3 make g++

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Runtime stage
FROM node:22-alpine AS runner
WORKDIR /app

# Install native compilation toolchain for SQLite in runtime environment
RUN apk add --no-cache python3 make g++

COPY package*.json ./
RUN npm ci --omit=dev

# Copy SQLite database, server wrapper, and the compiled Astro server build
COPY skincare.db ./
COPY server.mjs ./
COPY --from=builder /app/dist ./dist

# Bind server to the correct environment port required by Cloud Run
ENV HOST=0.0.0.0
ENV PORT=8080
EXPOSE 8080

CMD ["node", "./server.mjs"]
