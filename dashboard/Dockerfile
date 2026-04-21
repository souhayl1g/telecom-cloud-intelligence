FROM node:20-alpine
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ENV NEXT_PUBLIC_API_BASE_URL=http://api-gateway:8000
ENV AUTH_SERVICE_URL=http://auth-service:8002
ENV NEXT_PUBLIC_GRAFANA_URL=http://localhost:3000

EXPOSE 3001
ENV PORT=3001

CMD ["npm", "run", "dev", "--", "-p", "3001", "-H", "0.0.0.0"]
