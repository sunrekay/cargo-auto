# Deploying to a VPS

One command brings up the database, the API, the storefront and TLS:

```bash
make prod DOMAIN=cars.example.com ACME_EMAIL=you@example.com
```

nginx terminates TLS on 443 and proxies to the API; certbot obtains the Let's
Encrypt certificate and renews it in the background.

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
| services | starts the API, waits for its health check, then nginx and certbot |
| certificate | requests one from Let's Encrypt; on failure the placeholder stays and the site keeps serving |
| `prod-verify` | queries `/api/health` and prints the URLs |

### How the certificate is obtained

There is a chicken-and-egg problem: nginx will not start when `ssl_certificate`
points at a missing file, but certbot cannot obtain a certificate until nginx is
answering on port 80. The container breaks the circle by generating a
short-lived self-signed placeholder at the same path, so nginx always starts and
can answer the HTTP-01 challenge; certbot then overwrites it with the real
certificate and nginx is reloaded.

That also means a failed issuance never takes the site down — it stays up on the
placeholder, browsers warn, and `make prod-cert-issue` can be retried once DNS
or the firewall is sorted out.

Renewal runs every 12 hours in the certbot container, and nginx reloads every
6 hours to pick up a renewed certificate.

### Choosing the proxy

nginx is the default. Caddy remains available and issues certificates itself
with no certbot involved:

```bash
make prod PROXY=caddy DOMAIN=cars.example.com ACME_EMAIL=you@example.com
```

Only one of them can hold port 443, so this is an either/or choice.

Nothing in the sequence destroys data: the schema is `CREATE TABLE IF NOT EXISTS`
throughout, and the Postgres volume and Caddy's certificate store both persist
across `make prod-down` and redeploys.

## Day to day

```bash
make prod-logs          # follow everything
make prod-restart       # rebuild and restart API + proxy, leave the data alone
make prod-cert          # show the certificate currently installed
make prod-cert-issue    # obtain or renew it now
make prod-cert-staging  # same against the staging CA, for dry runs
make prod-down          # stop; data and certificates are kept
```

## Testing the certificate flow safely

Let's Encrypt rate-limits failed issuance — five failures per account, per
hostname, per hour. While shaking out a new host, use the staging CA:

```bash
make prod-cert-staging DOMAIN=cars.example.com ACME_EMAIL=you@example.com
```

Browsers flag a staging certificate as untrusted; that is expected. When the
flow works, delete the staging certificate and request a real one:

```bash
docker compose -f docker-compose.prod.yml run --rm --entrypoint \
  "certbot delete --cert-name cars.example.com" certbot
make prod-cert-issue DOMAIN=cars.example.com ACME_EMAIL=you@example.com
```

With `PROXY=caddy`, point Caddy at staging in `.env` instead:

```
ACME_CA_DIRECTIVE=acme_ca https://acme-staging-v02.api.letsencrypt.org/directory
```

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

Only the proxy publishes ports (80, 443). The API and Postgres are reachable
solely over the compose network and are not exposed to the internet.

nginx sends `X-Forwarded-Proto` and `X-Forwarded-For`, and the API runs with
`--proxy-headers`, so client addresses and the scheme survive the hop.

## Prices

The source lists prices in USD. `USD_RUB_RATE` in `.env` controls the rouble
figure the storefront shows; at `0` the site displays the original USD prices.
The rate is configuration and does not update itself — set it to whatever your
pricing policy uses, and the API reports it in every response so the number is
never opaque.
