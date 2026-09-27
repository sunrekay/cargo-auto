# Guazi.com car parser — Docker-based runner
SHELL := /bin/bash

# Docker Desktop on macOS does not always put the CLI on PATH
DOCKER := $(shell command -v docker 2>/dev/null || \
	(test -x $$HOME/.docker/bin/docker && echo $$HOME/.docker/bin/docker) || \
	(test -x /Applications/Docker.app/Contents/Resources/bin/docker && echo /Applications/Docker.app/Contents/Resources/bin/docker))
COMPOSE := $(DOCKER) compose

TARGET_CARS ?= 150
MAX_IMAGES_PER_CAR ?= 40
CONCURRENCY ?= 4
DOWNLOAD_IMAGES ?= 1
CITY ?= bin
VNC_PORT ?= 6080
PG_PORT ?= 55432
PROD := $(COMPOSE) -f docker-compose.prod.yml

# STAGING=1 asks Let's Encrypt's staging CA instead of the real one. Browsers
# reject staging certificates, so this is for rehearsing a deployment, never
# for serving visitors.
STAGING ?= 0

export TARGET_CARS MAX_IMAGES_PER_CAR CONCURRENCY DOWNLOAD_IMAGES CITY VNC_PORT
export DOCKER DOMAIN ACME_EMAIL STAGING DATABASE_URL

# Credentials for the local Postgres/pgAdmin live in .env
ifneq (,$(wildcard .env))
include .env
export
endif

.DEFAULT_GOAL := help
.PHONY: update help env check build up down login prod prod-init prod-ports prod-dns prod-verify prod-cert-issue prod-cert-staging prod-cert-reset prod-logs prod-down prod-restart prod-cert run recon shell vnc psql load-db backfill sqlite upload-s3 s3-status sql logs clean clean-data clean-profile clean-db stats csv

help: ## Show available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Vars: TARGET_CARS=$(TARGET_CARS) MAX_IMAGES_PER_CAR=$(MAX_IMAGES_PER_CAR) CONCURRENCY=$(CONCURRENCY)"
	@echo "  Ports: noVNC=$(VNC_PORT) Postgres=$(PG_PORT)"
	@echo "  Rehearse TLS without burning rate limits:  make prod DOMAIN=… ACME_EMAIL=… STAGING=1"

env: ## Create .env from the example if it is missing
	@test -f .env || { cp .env.example .env; echo "created .env — set the two passwords in it"; }

check: ## Verify docker + compose are available and the daemon is up
	@test -n "$(DOCKER)" || { echo "docker CLI not found — install/start Docker Desktop"; exit 1; }
	@echo "docker:  $$($(DOCKER) --version)"
	@echo "compose: $$($(COMPOSE) version --short 2>/dev/null || echo MISSING)"
	@$(DOCKER) info --format 'daemon:  {{.ServerVersion}} ({{.OSType}}/{{.Architecture}})' 2>/dev/null || \
		{ echo "daemon not running — start Docker Desktop"; exit 1; }
	@test -f .env && echo ".env:    present" || echo ".env:    MISSING — run 'make env'"

build: check ## Build the parser and pgAdmin images
	$(COMPOSE) build

up: build ## Start Postgres in the background
	$(COMPOSE) up -d postgres
	@echo "  Postgres  ->  localhost:$(PG_PORT)  db=$(POSTGRES_DB) user=$(POSTGRES_USER)"

down: ## Stop all services (the data volume is kept)
	$(COMPOSE) down

login: build ## Step 1 — open the live browser; YOU clear the site check / sign in
	@mkdir -p data
	@echo ""
	@echo "  A Chromium window will start inside the container."
	@echo "  Open  ->  http://localhost:$(VNC_PORT)/   and clear the check there."
	@echo "  Credentials you type go straight to the site; the parser only reuses cookies."
	@echo ""
	$(COMPOSE) run --rm --service-ports login

run: build up ## Step 2 — parse TARGET_CARS cars into ./data + Postgres (default 150)
	@mkdir -p data/images
	@test -d data/profile || echo "  note: no browser profile yet — run 'make login' first"
	$(COMPOSE) run --rm --service-ports parser

recon: build ## Probe the site structure, dump HTML/selectors to ./data/recon
	@mkdir -p data/recon
	$(COMPOSE) run --rm --service-ports recon

shell: build ## Open a shell inside the container
	$(COMPOSE) run --rm --entrypoint bash parser

vnc: ## Print the noVNC address of a running container
	@echo "http://localhost:$(VNC_PORT)/"

psql: ## Open a psql shell on the parsed data
	$(COMPOSE) exec postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

sql: ## Run one query, e.g. make sql Q="select make, count(*) from cars group by 1"
	@test -n "$(Q)" || { echo 'usage: make sql Q="select ..."'; exit 1; }
	@$(COMPOSE) exec -T postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "$(Q)"

load-db: up ## Load an existing data/cars.json into Postgres (no re-crawl)
	$(COMPOSE) run --rm --no-deps -e DATABASE_URL="postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@postgres:5432/$(POSTGRES_DB)" \
		--entrypoint "python -m parser.main load-db" parser

logs: ## Tail the parser log
	@tail -f data/parser.log

stats: ## Summarise what has been collected
	@test -f data/cars.json && python3 -c "import json,os; \
d=json.load(open('data/cars.json')); \
print(f'cars: {len(d)}'); \
print('images:', sum(len(c.get(\"images\",[])) for c in d)); \
print('files: ', sum(len(fs) for _,_,fs in os.walk('data/images')))" || echo "no data yet — run 'make run'"

upload-s3: ## Upload downloaded photos to the S3 bucket (idempotent)
	$(COMPOSE) run --rm --no-deps --entrypoint "python -m parser.s3 sync" parser

s3-status: ## How many photos are already in the bucket
	@$(COMPOSE) run --rm --no-deps --entrypoint "python -m parser.s3 status" parser

backfill: ## Fill make/model/colour/drive/seats from each car's URL (no re-crawl)
	$(COMPOSE) run --rm --no-deps --entrypoint "python -m parser.main backfill" parser

sqlite: ## Export the Postgres catalogue into data/cargo-auto.db (ships with the repo)
	$(COMPOSE) run --rm --no-deps --entrypoint "python -m tools.export_sqlite" parser

csv: ## Rebuild CSV from cars.json without re-parsing
	$(COMPOSE) run --rm --entrypoint "python -m parser.export" parser

# ---------------------------------------------------------------- production
prod: ## Deploy: preflight -> build -> healthy services -> TLS -> public verification
	@bash scripts/prod-start.sh

update: ## Fast-forward the checkout, then deploy
	git pull --ff-only
	git submodule update --init --recursive
	@$(MAKE) prod

prod-init: ## Checks and scaffolding that must pass before the stack starts
	@bash scripts/prod-check.sh
	@test -n "$(DOCKER)" || { echo "docker CLI not found"; exit 1; }
	@$(DOCKER) info >/dev/null 2>&1 || { echo "docker daemon is not running"; exit 1; }
	@test -f .env || { cp .env.example .env; echo "created .env from the example"; }
	@grep -q '^POSTGRES_PASSWORD=.\+' .env || { \
		pw=$$(head -c 24 /dev/urandom | base64 | tr -d '/+=' | cut -c1-24); \
		if grep -q '^POSTGRES_PASSWORD=' .env; then \
			sed -i.bak "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$$pw|" .env && rm -f .env.bak; \
		else echo "POSTGRES_PASSWORD=$$pw" >> .env; fi; \
		echo "generated a database password into .env (used only with the postgres profile)"; }
	@test -n "$(DOMAIN)" || { \
		echo ""; \
		echo "  DOMAIN is not set."; \
		echo "  Put it in .env (DOMAIN=cars.example.com) or pass it:"; \
		echo "      make prod DOMAIN=cars.example.com ACME_EMAIL=you@example.com"; \
		echo ""; \
		echo "  The domain needs an A record pointing at this host, and ports"; \
		echo "  80 and 443 reachable — Let's Encrypt verifies over HTTP."; \
		exit 1; }
	@test -n "$(ACME_EMAIL)" || { echo "ACME_EMAIL is not set (used for certificate expiry notices)"; exit 1; }
	@set -e; tmp=$$(mktemp .env.prod.XXXXXX); \
		awk '!/^DOMAIN=/ && !/^ACME_EMAIL=/' .env > "$$tmp"; \
		printf 'DOMAIN=%s\nACME_EMAIL=%s\n' "$(DOMAIN)" "$(ACME_EMAIL)" >> "$$tmp"; \
		chmod 600 "$$tmp" && mv "$$tmp" .env
	@test -d web || { echo "storefront missing: web/ is not present"; exit 1; }
	@$(PROD) config --quiet
	@mkdir -p data/images
	@echo "==> checks passed: domain $(DOMAIN), storefront present, .env complete"
	@$(MAKE) --no-print-directory prod-ports
	@$(MAKE) --no-print-directory prod-dns

prod-ports: ## Report every process listening on 80 and 443
	@sh scripts/check-ports.sh

prod-dns: ## Require DNS resolution before spending ACME validation attempts
	@if command -v getent >/dev/null 2>&1; then \
		getent hosts "$(DOMAIN)" >/dev/null; \
	elif command -v dscacheutil >/dev/null 2>&1; then \
		dscacheutil -q host -a name "$(DOMAIN)" | grep -q 'ip_address:'; \
	else echo "Install getent to check DNS" >&2; exit 1; fi \
	|| { echo "DOMAIN does not resolve; fix DNS before make prod" >&2; exit 1; }

prod-verify: ## Verify public HTTPS, storefront and API; fail if any route is unavailable
	@bash scripts/prod-verify.sh

prod-logs: ## Follow the production logs
	$(PROD) logs -f --tail=80

prod-down: ## Stop the production stack (data and certificates are kept)
	$(PROD) down

prod-restart: ## Rebuild and restart API and proxy, leaving the data alone
	$(PROD) build api nginx && $(PROD) up -d --remove-orphans

prod-cert-issue: ## Obtain or renew the domain certificate; failures stop deployment
	@bash scripts/prod-cert.sh

prod-cert-staging: ## Request a staging certificate (untrusted by browsers)
	@$(MAKE) --no-print-directory prod-cert-issue STAGING=1

prod-cert-reset: ## Delete every certificate for DOMAIN (after a staging rehearsal)
	@test -n "$(DOMAIN)" || { echo "DOMAIN is not set"; exit 1; }
	@$(PROD) run --rm -v ./scripts:/scripts:ro --entrypoint sh certbot \
		/scripts/cert-reset.sh $(DOMAIN)
	@echo "  ACME state reset; published pair retained until successful issuance"

prod-cert: ## Show the certificate currently installed
	@$(PROD) exec -T nginx sh -c \
		'openssl x509 -in "/etc/nginx/public/current/fullchain.pem" -noout -subject -issuer -dates'


clean: ## Remove the image and containers
	-$(COMPOSE) down --rmi local -v

clean-data: ## Delete all parsed data (irreversible)
	rm -rf data/cars.json data/cars.csv data/images data/raw data/recon data/parser.log data/state.json

clean-profile: ## Forget the browser profile (you will re-do the site check)
	rm -rf data/profile

clean-db: ## Drop the Postgres volume (irreversible)
	-$(COMPOSE) down -v
