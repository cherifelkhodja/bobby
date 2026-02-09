# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Force fresh copy - change this value to bust Docker cache
RUN echo "build-20260209-v3"

# Copy source and build
COPY . .

# Build with environment variable for API URL
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Production stage with nginx
FROM nginx:alpine

# Force stage-1 rebuild
RUN echo "stage1-20260209-v3"

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Railway uses PORT env variable - nginx needs to listen on it
# We'll use envsubst to replace the port in nginx config
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
