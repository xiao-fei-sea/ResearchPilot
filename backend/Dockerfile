# 后端镜像：api 与 worker 共用，命令由 compose 指定
FROM python:3.12-slim

WORKDIR /app

# 先装依赖利用层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium --with-deps || true

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
