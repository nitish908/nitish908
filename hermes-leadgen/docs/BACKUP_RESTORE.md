# Backup & Restore

The only stateful service is PostgreSQL (Redis holds only ephemeral
Celery broker/result data — safe to lose). Back up the Postgres volume.

## Backup

### Ad hoc dump

```bash
docker compose exec -T postgres pg_dump -U hermes hermes_leadgen | gzip > "backup-$(date +%Y%m%d-%H%M%S).sql.gz"
```

### Scheduled backup (cron on the host)

```bash
# /etc/cron.d/hermes-leadgen-backup
0 3 * * * root cd /path/to/hermes-leadgen-deploy/hermes-leadgen && \
  docker compose exec -T postgres pg_dump -U hermes hermes_leadgen | gzip > /var/backups/hermes-leadgen/backup-$(date +\%Y\%m\%d).sql.gz \
  && find /var/backups/hermes-leadgen -name '*.sql.gz' -mtime +30 -delete
```

Create the target directory first: `sudo mkdir -p /var/backups/hermes-leadgen`.

Copy backups off the VPS regularly (S3, another host, etc.) — a backup
that lives only on the machine it's backing up doesn't survive that
machine's disk failure.

### What's *not* covered by a Postgres dump

- Provider credentials are stored **encrypted** in the `source_credentials`
  table — the dump includes the ciphertext, but restoring it is only
  useful if you also have `CREDENTIALS_ENCRYPTION_KEY` from the original
  `.env`. **Back up your `.env` file separately, and treat it as secret
  material** (e.g. a password manager or encrypted secret store, not a
  plaintext copy alongside the SQL dump).
- Uploaded CSV files are not retained after import (only the resulting
  `Lead` rows are) — nothing to back up there.

## Restore

### Full restore to a fresh instance

```bash
# 1. Bring up just Postgres
docker compose up -d postgres
sleep 5

# 2. Drop and recreate the database (destroys current data — confirm first)
docker compose exec -T postgres psql -U hermes -d postgres -c "DROP DATABASE IF EXISTS hermes_leadgen;"
docker compose exec -T postgres psql -U hermes -d postgres -c "CREATE DATABASE hermes_leadgen OWNER hermes;"

# 3. Restore the dump
gunzip -c backup-YYYYMMDD-HHMMSS.sql.gz | docker compose exec -T postgres psql -U hermes -d hermes_leadgen

# 4. Restore the matching .env (same CREDENTIALS_ENCRYPTION_KEY as when the backup was taken)
cp /secure/location/.env .env

# 5. Start everything else
docker compose up -d --build
```

### Point-in-time considerations

`pg_dump` captures a consistent snapshot at the moment it runs, not
continuous point-in-time recovery. If you need PITR (e.g. "restore to
2 minutes before an accidental bulk delete"), configure Postgres WAL
archiving separately — out of scope for this MVP's tooling.

## Verifying a backup is actually restorable

Periodically restore a backup into a throwaway container and check it:

```bash
docker run --rm -d --name restore-test -e POSTGRES_PASSWORD=test postgres:16-alpine
sleep 5
gunzip -c backup-YYYYMMDD-HHMMSS.sql.gz | docker exec -i restore-test psql -U postgres
docker exec restore-test psql -U postgres -c "SELECT count(*) FROM leads;"
docker stop restore-test
```

A backup you've never test-restored is a backup you don't actually have.

## Disaster-recovery checklist

1. Provision a new VPS, install Docker (§1 of `DEPLOYMENT_UBUNTU.md`)
2. Restore `.env` from secure storage
3. Restore the Postgres dump (steps above)
4. `docker compose up -d --build`
5. Verify `/api/health`, log in, spot-check a few leads
6. Re-point DNS if the IP changed
