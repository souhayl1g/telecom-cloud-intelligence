FROM node:20-alpine
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ENV NEXT_PUBLIC_API_BASE_URL=http://api-gateway:8000
ENV AUTH_SERVICE_URL=http://auth-service:8002
ENV NEXT_PUBLIC_GRAFANA_URL=http://localhost:3000

# Production build — eliminates per-request webpack recompile that was
# adding 1-15 seconds of latency per dev-mode API route hit.
RUN npm run build

EXPOSE 3001
ENV PORT=3001
ENV NODE_ENV=production

CMD ["npm", "start", "--", "-p", "3001", "-H", "0.0.0.0"]
