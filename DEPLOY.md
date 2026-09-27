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
3. **Have the storefront present.** `web/index.html` must exist in this checkout.
4. **Use Docker Compose with `up --wait` support.** Docker Compose v2 is required.

## What `make prod` does

The ordered `scripts/prod-start.sh` workflow follows the deployment approach in
`genmail_server`, adapted to this project's API/nginx/certbot stack:

1. Validate domain, email, Docker/Compose, curl, storefront and SQLite catalogue
   before any build. PostgreSQL URLs do not require a local SQLite file.
   Persist the effective domain/email in `.env`, validate Compose configuration,
   report port listeners and require DNS resolution (not a match to a local IP).
2. Build only API and nginx images.
3. Start API and nginx with `--wait --wait-timeout 180`. When DATABASE_URL points
   to the Compose host `postgres`, start its profile and wait first; an existing
   database is not reset. External PostgreSQL must already be reachable.
4. Issue or renew the certificate with `--keep-until-expiring`. A certbot failure
   stops deployment. Restart nginx to switch from its placeholder, validate its
   configuration, then start the background renewal service.
5. Request the public HTTPS routes `/api/health`, `/`, and `/api/cars` with normal
   TLS validation. Any failed route makes the command fail instead of printing
   a successful deployment. Each route gets up to 30 attempts (5s request timeout,
   2s between attempts).
6. Print the site and API addresses only after the checks pass.

Like the reference project, `make update` runs `git pull --ff-only`, updates pinned
submodules, then runs `make prod`. No automatic global Docker pruning is performed;
other projects may share the Docker daemon. No internal PKI or application
migrations are added: this stack uses the supplied catalogue and public TLS.

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

Nothing in the sequence destroys data: the schema is `CREATE TABLE IF NOT EXISTS`
throughout, and both the data and the certificate volumes persist across
`make prod-down` and redeploys.

## Day to day

```bash
make update             # pull --ff-only, update submodules, deploy
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
make prod DOMAIN=cars.example.com ACME_EMAIL=you@example.com STAGING=1
```

Browsers flag a staging certificate as untrusted; that is expected. When the
flow works, delete the staging certificate and request a real one:

```bash
make prod-cert-reset DOMAIN=cars.example.com
make prod DOMAIN=cars.example.com ACME_EMAIL=you@example.com
```

Staging runs verify the API internally and explicitly report a rehearsal, not a
trusted public HTTPS deployment. A production certificate is never replaced by
staging automatically; a staging certificate blocks production until explicitly
reset. Failed issuance keeps existing containers/data intact but returns an error.


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
