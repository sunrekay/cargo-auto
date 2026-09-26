FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /bin/
COPY backend/requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY backend/ ./backend/

EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
