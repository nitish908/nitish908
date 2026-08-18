# Deployment Guide: Ubuntu VPS

Tested against Ubuntu 22.04/24.04 LTS. Assumes a fresh VPS with a
non-root sudo user and a domain name pointed at it (for TLS).

## 1. Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker
docker --version
docker compose version
```

## 2. Clone the repository and configure

```bash
git clone <your-fork-url> hermes-leadgen-deploy
cd hermes-leadgen-deploy/hermes-leadgen
cp .env.example .env
```

Edit `.env`:

```bash
# Required
python3 -c "import secrets; print(secrets.token_urlsafe(48))"                                # -> SECRET_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"   # -> CREDENTIALS_ENCRYPTION_KEY
```

Set at minimum:
- `SECRET_KEY`, `CREDENTIALS_ENCRYPTION_KEY` (generated above)
- `SEED_OWNER_EMAIL`, `SEED_OWNER_PASSWORD` (your first login)
- `COOKIE_SECURE=true` (should already be the default — required for a
  real HTTPS deployment)
- `CORS_ORIGINS=["https://your-domain.com"]`
- `NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.com` (or whatever
  path routes to the backend through your reverse proxy)
- `SENDER_NAME`, `SENDER_COMPANY`, `SENDER_CONTACT_EMAIL` — used in every
  generated outreach draft
- Leave `OUTREACH_LIVE_SEND_ENABLED=false` until you've reviewed
  `docs/COMPLIANCE_CHECKLIST.md` and configured real SMTP credentials

**Never commit `.env`.** It's already git-ignored.

## 3. Put a reverse proxy + TLS in front of it

`docker-compose.yml` exposes the backend on `:8000` and the frontend on
`:3000` directly — fine for local development, not for production. Put
Caddy or nginx + certbot in front. Minimal Caddy example
(`/etc/caddy/Caddyfile`):

```caddy
your-domain.com {
    reverse_proxy localhost:3000
}

api.your-domain.com {
    reverse_proxy localhost:8000
}
```

```bash
sudo apt install -y caddy   # or your distro's package
sudo systemctl restart caddy
```

Caddy handles TLS certificate issuance/renewal automatically. If using
nginx instead, run certbot separately and configure the two server blocks
similarly.

## 4. Build the frontend for production

The bundled `docker-compose.yml` runs `npm run dev` for the frontend,
which is convenient for local development but not production-grade
(no minified build, dev server overhead). For a VPS deployment, override
the frontend service's command:

```yaml
# docker-compose.prod.yml (overlay)
services:
  frontend:
    command: sh -c "npm run build && npm run start"
```

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## 5. Start everything

```bash
docker compose up -d --build
docker compose logs -f backend   # watch migrations + seed run
```

On first boot the `backend` service runs `alembic upgrade head`, seeds
the default scoring rules, and creates your owner account from
`SEED_OWNER_EMAIL`/`SEED_OWNER_PASSWORD`.

## 6. Verify

```bash
curl https://api.your-domain.com/api/health
# {"status":"ok"}
```

Visit `https://your-domain.com`, sign in, and run through
`docs/DEMO_WORKFLOW.md`.

## 7. Celery beat (the daily workflow)

`docker compose up` already starts a `worker` and a `beat` container. Beat
fires the daily workflow at 07:00 UTC by default
(`app/workers/celery_app.py`). To change the time, edit the `crontab(...)`
call there and rebuild, or override `DAILY_DISCOVERY_LEAD_LIMIT` in `.env`
to change how many leads it processes per run.

Check it's running:

```bash
docker compose logs -f beat
docker compose logs -f worker
```

## 8. Keeping it updated

```bash
git pull
docker compose up -d --build   # rebuilds changed images, re-runs migrations
```

Alembic migrations are additive/linear; `alembic upgrade head` on startup
handles applying new ones. Always back up before a deploy that includes a
schema change — see `docs/BACKUP_RESTORE.md`.

## 9. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80,443/tcp
sudo ufw enable
```

Do **not** expose Postgres (`5432`) or Redis (`6379`) publicly — the
`docker-compose.yml` port mappings for those are for local development
convenience; remove or bind them to `127.0.0.1` in production
(`127.0.0.1:5432:5432`).

## 10. Monitoring

Minimum viable monitoring for a small deployment:

```bash
docker compose ps                 # container health
docker compose logs --tail 200    # recent logs across services
```

For anything beyond a single-operator MVP, wire up a real log aggregator
and uptime check against `/api/health` — not included by default.
