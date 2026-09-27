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

The ordered `scripts/prod-start.sh` workflow deploys the API/nginx/certbot stack:

1. Validate domain, email, Docker/Compose, curl, storefront and SQLite catalogue
   before any build. PostgreSQL URLs do not require a local SQLite file.
   Persist the effective domain/email in `.env`, validate Compose configuration,
   report port listeners and require DNS resolution (not a match to a local IP).
2. Build API, nginx and the certificate helper image.
3. Validate an existing certificate (hostname, key match, expiry and trusted chain).
   Reuse it if at least 30 days remain. Otherwise stop only this project's nginx
   and renewal worker, and issue via Certbot standalone on port 80. Other host
   services are never stopped automatically; port conflicts stop issuance.
4. Publish the validated certificate/key into the separate `public_tls` volume,
   switching one symlink for both files. Start API and nginx with
   `--wait --wait-timeout 180`, then the renewal worker. Local PostgreSQL is started
   first only when DATABASE_URL points to the Compose host `postgres`.
5. Request public HTTPS `/api/health`, `/`, and `/api/cars` with normal TLS
   validation. Failure is fatal; curl's reason is printed. No `--insecure` fallback.
6. Print the site/API addresses after all checks pass.

`make update` fast-forwards the checkout, updates pinned submodules, and invokes
`make prod`. No global Docker pruning is performed.

### Certificate storage and first startup

The `letsencrypt` volume is private Certbot state. The proxy reads only the
validated pair from `public_tls:/etc/nginx/public/current`. No placeholder is
created, and nginx refuses to start without a published certificate.

Initial issuance does not depend on nginx: Certbot serves HTTP-01 itself on port
80. A short interruption is expected when an existing stack needs standalone
issuance; a valid reusable certificate avoids this stop. On failure the script
attempts to start previously running containers again and exits with an error.
Data volumes and old published certificate bundles are retained.

### Renewal

The worker runs every 12 hours using `--webroot`, overriding standalone from
initial issuance. A deploy hook validates and atomically publishes the new pair.
Nginx watches the published symlink every 60 seconds; it tests configuration and
reloads only after a successful change. The site stays online during renewal.

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

## Public health check fails although the API is healthy

An internal HTTP 200 does not prove public TLS is valid. `make prod-verify` prints
the underlying curl error; certificate error 60 stops immediately. Inspect the
published certificate with `make prod-cert`. Never use `curl -k` to mark a deploy ready.

Older deployments may have a self-signed placeholder in
`/etc/letsencrypt/live/<domain>`. `make prod-cert-issue` detects this by matching
issuer and subject. Unmanaged placeholders are moved to
`/etc/letsencrypt/legacy-backups/` before issuance, preserving the keys and
certificate. If a self-signed or missing certificate also has a malformed renewal file
(missing required file references), its live directory, archive and renewal file
are moved together into the backup. Other domains and CA-issued certificates are
not moved. Complete managed lineages require explicit inspection/reset.
After issuance, the script confirms that the mounted certificate was replaced
before starting nginx. Then run `make prod-verify`.
