# Deploying to a VPS

One command brings up the database, the API, the storefront and TLS:

```bash
make prod DOMAIN=cars.example.com ACME_EMAIL=you@example.com
```

Caddy obtains the Let's Encrypt certificate on first start and renews it on its
own — there is no certbot, no cron entry and no renewal hook to maintain.

## Before the first run

1. **Point the domain at the server.** An `A` record for `DOMAIN` must resolve to
   this host's public IP. `make prod` checks this and warns when it does not
   match, because the ACME challenge will otherwise fail.
2. **Open ports 80 and 443.** Let's Encrypt validates over HTTP on port 80, and
   the site is served on 443. Both must be reachable from the internet.
3. **Have the storefront present.** `cargo-auto/` is the frontend; clone it next
   to this project if it is missing.

## What `make prod` does

`prod` runs `prod-init` first and refuses to start if anything is missing:

| Step | What it checks or creates |
|---|---|
| `prod-init` | docker present and running; `.env` exists (created from the example if not); a database password (generated if absent); `DOMAIN` and `ACME_EMAIL` set and recorded in `.env`; the storefront directory; `data/images` |
| `prod-dns` | whether `DOMAIN` resolves to this host, warning early instead of failing inside ACME |
| build | images for the API (and the parser when you use it) |
| database | starts Postgres, waits for it to accept connections, applies `db/schema.sql` — idempotent, so it is safe on every deploy |
| services | starts the API, waits for its health check, then starts Caddy |
| `prod-verify` | queries `/api/health` and prints the URLs |

Nothing in the sequence destroys data: the schema is `CREATE TABLE IF NOT EXISTS`
throughout, and the Postgres volume and Caddy's certificate store both persist
across `make prod-down` and redeploys.

## Day to day

```bash
make prod-logs      # follow everything
make prod-restart   # rebuild and restart API + proxy, leave the database alone
make prod-cert      # show the issued certificate
make prod-down      # stop; data and certificates are kept
```

## Testing the certificate flow safely

Let's Encrypt rate-limits failed issuance. While shaking out a new host, point
Caddy at the staging CA in `.env`:

```
ACME_CA_DIRECTIVE=acme_ca https://acme-staging-v02.api.letsencrypt.org/directory
```

Browsers will flag the staging certificate as untrusted — that is expected.
Clear the variable and `make prod-restart` for a real one.

## Filling the catalogue

The crawler is deliberately **not** part of the production stack: it needs a
browser and occasional human input for the source site's anti-bot check, which
does not belong on a web server. Run it where you can watch it, then move the
data over:

```bash
make run                      # collect cars into ./data and Postgres
make backfill                 # complete records from saved pages, no re-crawl
make upload-s3                # push photos to object storage
```

With `S3_BUCKET` set, the API serves photo URLs straight from object storage and
the VPS never has to hold the image files. Without it, mount `./data/images` on
the server and the API serves them from `/media`.

## Ports and exposure

Only Caddy publishes ports (80, 443). Postgres and the API are reachable solely
over the compose network — the database is not exposed to the internet at all.

## Prices

The source lists prices in USD. `USD_RUB_RATE` in `.env` controls the rouble
figure the storefront shows; at `0` the site displays the original USD prices.
The rate is configuration and does not update itself — set it to whatever your
pricing policy uses, and the API reports it in every response so the number is
never opaque.
