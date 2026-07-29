# Packages the trading agent to run as `trading_agent.server` -- a stateless
# HTTP wrapper around a single poll, meant to be driven by an external
# scheduler (e.g. a Cloudflare Durable Object alarm via `schedule()`; see
# cloudflare/worker/src/index.ts). Cloudflare Containers require the app to
# listen on port 8080.
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY src ./src
COPY config ./config
COPY data ./data

RUN pip install --no-cache-dir -e .

ENV PORT=8080
EXPOSE 8080

CMD ["python", "-m", "trading_agent.server"]
