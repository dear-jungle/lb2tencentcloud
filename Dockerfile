# 阶段 1：前端构建
FROM node:20-alpine AS frontend-builder
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./frontend/
RUN cd frontend && npm ci --production=false
COPY public/ ./public/
COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# 阶段 2：Python 应用
FROM python:3.10-slim
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/
COPY server.py .
COPY start.sh .
COPY migrations/ ./migrations/
RUN chmod +x start.sh

# 复制前端构建产物
COPY --from=frontend-builder /build/dist/ ./dist/

# 同时保留 public 目录（开发模式回退）
COPY public/ ./public/

# 创建日志目录
RUN mkdir -p logs

EXPOSE 10041

ENV DEV_MODE=0
ENV PORT=10041
ENV WORKERS=4

CMD ["./start.sh", "--prod"]
