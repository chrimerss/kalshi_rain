FROM node:20-alpine AS builder

WORKDIR /app
RUN mkdir -p /backend/data

COPY frontend/package*.json ./
RUN npm install

COPY frontend ./
# Build Next.js app
RUN npm run build

# Runner stage
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV production

# Copy built artifacts and dependencies
COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
# Copy src/lib/db.ts logic depends on path relative to backend
# Frontend code at runtime (server side) needs access to DB file.
# In dev: `path.resolve(process.cwd(), '../backend/data/raincheck.db')`
# process.cwd() is /app in container.
# So we need to map volume to `/backend/data` inside container?
# Or `/app/backend/data`?
# Builder creates standard structure.
# Let's ensure creating `/app/backend/data` directory exists.

RUN mkdir -p /app/backend/data

EXPOSE 3000

CMD ["npm", "start"]
