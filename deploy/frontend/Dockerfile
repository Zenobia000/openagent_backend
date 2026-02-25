# OpenCode Platform - Frontend Dockerfile

# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# 複製 package files
COPY frontend/package*.json ./

# 安裝依賴
RUN npm ci

# 複製源碼
COPY frontend/ ./

# 設置 API URL（構建時）
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

# 構建
RUN npm run build

# Production stage
FROM nginx:alpine

# 複製構建產物
COPY --from=builder /app/dist /usr/share/nginx/html

# 複製 nginx 配置
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
