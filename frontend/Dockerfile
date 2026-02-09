# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Force fresh copy - change this value to bust Docker cache
RUN echo "build-20260209-v4"

# Copy source and build
COPY . .

# Build with environment variable for API URL
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Production stage with nginx (pinned version for stability)
FROM nginx:1.27-alpine

# Force stage-1 rebuild
RUN echo "stage1-20260209-v4"

# Remove default config and use nginx templates mechanism
# nginx will auto-envsubst files in /etc/nginx/templates/ on startup
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Default PORT for Railway (overridden by Railway's PORT env var)
ENV PORT=80
# Only substitute PORT in nginx templates (protect $uri and other nginx variables)
ENV NGINX_ENVSUBST_FILTER=^PORT$

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
