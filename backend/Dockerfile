# Dockerfile for the AI Chess Coach backend.
# Using Docker (instead of Render's native Python runtime) because
# installing Stockfish via apt requires root access during the build,
# which Render's native runtime does not allow.

FROM python:3.12-slim

# Install Stockfish as a system package
RUN apt-get update && \
    apt-get install -y --no-install-recommends stockfish && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render sets $PORT at runtime; default to 8000 for local docker runs
ENV PORT=8000
EXPOSE 8000

CMD uvicorn api:app --host 0.0.0.0 --port $PORT