# Stage 1: Build the Angular app
FROM node:16 AS builder
WORKDIR /app
ENV NG_BUILD_MAX_WORKERS=2
ENV NODE_OPTIONS=--max-old-space-size=1536
COPY package*.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build -- --configuration production

# Stage 2: Serve the Angular app using Nginx
FROM nginx:alpine
COPY --from=builder /app/dist/pharma-go /usr/share/nginx/html
# Copy custom Nginx configuration file
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
