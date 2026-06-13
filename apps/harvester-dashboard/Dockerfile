# Use node with pnpm pre-installed or install it
FROM node:20-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# 1. Copy workspace metadata
# We must copy root files for pnpm to recognize the workspace
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
# Copy package.json of the apps and packages involved
COPY apps/harvester-dashboard/package.json ./apps/harvester-dashboard/
COPY packages/api-spec/package.json ./packages/api-spec/

# Install dependencies for the whole workspace (optimized by pnpm)
RUN pnpm install --frozen-lockfile

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/harvester-dashboard/node_modules ./apps/harvester-dashboard/node_modules
COPY . .

# Disable telemetry and build-time linting for speed
ENV NEXT_TELEMETRY_DISABLED 1

# NEXT_PUBLIC_* vars are baked into the client bundle at build time by `next build`.
# Runtime env vars cannot override them — pass these via --build-arg.
# NEXT_PUBLIC_API_URL is required for staging/production. Omitting it fails the build.
# Local dev: use .env.local (not Docker) or pass via docker-compose build args.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

ARG NEXT_PUBLIC_MAPBOX_TOKEN=""
ENV NEXT_PUBLIC_MAPBOX_TOKEN=$NEXT_PUBLIC_MAPBOX_TOKEN

ARG NEXT_PUBLIC_KEYCLOAK_URL
ENV NEXT_PUBLIC_KEYCLOAK_URL=$NEXT_PUBLIC_KEYCLOAK_URL

ARG NEXT_PUBLIC_KEYCLOAK_REALM
ENV NEXT_PUBLIC_KEYCLOAK_REALM=$NEXT_PUBLIC_KEYCLOAK_REALM

ARG NEXT_PUBLIC_KEYCLOAK_CLIENT_ID
ENV NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=$NEXT_PUBLIC_KEYCLOAK_CLIENT_ID

WORKDIR /app/apps/harvester-dashboard
RUN pnpm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/apps/harvester-dashboard/public ./public

# Automatically leverage output traces to reduce image size
# https://nextjs.org/docs/advanced-features/output-file-tracing
COPY --from=builder --chown=nextjs:nodejs /app/apps/harvester-dashboard/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/harvester-dashboard/.next/static ./apps/harvester-dashboard/.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000
# set hostname to localhost
ENV HOSTNAME "0.0.0.0"

# server.js is created by next build in standalone mode
CMD ["node", "apps/harvester-dashboard/server.js"]
