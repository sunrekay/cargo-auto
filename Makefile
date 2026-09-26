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

export TARGET_CARS MAX_IMAGES_PER_CAR CONCURRENCY DOWNLOAD_IMAGES CITY VNC_PORT

# Credentials for the local Postgres/pgAdmin live in .env
ifneq (,$(wildcard .env))
include .env
export
endif

.DEFAULT_GOAL := help
.PHONY: help env check build up down login prod prod-init prod-dns prod-verify prod-logs prod-down prod-restart prod-cert run recon shell vnc psql load-db backfill sqlite upload-s3 s3-status sql logs clean clean-data clean-profile clean-db stats csv

help: ## Show available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Vars: TARGET_CARS=$(TARGET_CARS) MAX_IMAGES_PER_CAR=$(MAX_IMAGES_PER_CAR) CONCURRENCY=$(CONCURRENCY)"
	@echo "  Ports: noVNC=$(VNC_PORT) Postgres=$(PG_PORT)"

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
prod: ## Bring the whole stack up on a VPS with TLS (make prod DOMAIN=… ACME_EMAIL=…)
	@$(MAKE) --no-print-directory prod-init
	@echo "==> building images"
	$(PROD) build
	@echo "==> catalogue: $(shell test -f data/cargo-auto.db && echo 'data/cargo-auto.db' || echo 'MISSING — run make sqlite')"
	@test -f data/cargo-auto.db || { echo "no catalogue to serve"; exit 1; }
	@echo "==> starting API and TLS proxy"
	$(PROD) up -d api caddy
	@$(MAKE) --no-print-directory prod-verify

prod-init: ## Checks and scaffolding that must pass before the stack starts
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
	@grep -q '^DOMAIN=' .env || echo "DOMAIN=$(DOMAIN)" >> .env
	@grep -q '^ACME_EMAIL=' .env || echo "ACME_EMAIL=$(ACME_EMAIL)" >> .env
	@test -d web || { echo "storefront missing: web/ is not present"; exit 1; }
	@mkdir -p data/images
	@echo "==> checks passed: domain $(DOMAIN), storefront present, .env complete"
	@$(MAKE) --no-print-directory prod-dns

prod-dns: ## Warn when the domain does not resolve to this host
	@ip=$$(curl -s --max-time 5 https://api.ipify.org || true); \
	dns=$$(getent hosts $(DOMAIN) 2>/dev/null | awk '{print $$1}' | head -1); \
	if [ -n "$$ip" ] && [ -n "$$dns" ] && [ "$$ip" != "$$dns" ]; then \
		echo "  warning: $(DOMAIN) resolves to $$dns but this host is $$ip"; \
		echo "           Let's Encrypt will fail until the A record matches"; \
	elif [ -z "$$dns" ]; then \
		echo "  warning: $(DOMAIN) does not resolve yet — certificate issuance will fail"; \
	else echo "==> DNS ok: $(DOMAIN) -> $$dns"; fi

prod-verify: ## Report what the running stack answers
	@echo "==> waiting for the API"
	@for i in $$(seq 1 30); do \
		$(PROD) exec -T api python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)" >/dev/null 2>&1 && break; \
		printf "."; sleep 2; done; echo ""
	@$(PROD) exec -T api python -c "import urllib.request,json;print('  API:', json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=5)))" 2>/dev/null \
		|| echo "  API did not answer — check 'make prod-logs'"
	@echo ""
	@echo "  site      ->  https://$(DOMAIN)/"
	@echo "  API       ->  https://$(DOMAIN)/api/cars"
	@echo "  photos    ->  https://$(DOMAIN)/media/<car-id>/<file>"
	@echo ""
	@echo "  The first request may take ~30s while Let's Encrypt issues the certificate."
	@echo "  Watch it happen:  make prod-logs"

prod-logs: ## Follow the production logs
	$(PROD) logs -f --tail=80

prod-down: ## Stop the production stack (data and certificates are kept)
	$(PROD) down

prod-restart: ## Rebuild and restart API and proxy without touching the database
	$(PROD) build api && $(PROD) up -d api caddy

prod-cert: ## Show the issued certificate
	@$(PROD) exec -T caddy sh -c 'ls -R /data/caddy/certificates 2>/dev/null' || echo "no certificate yet"


clean: ## Remove the image and containers
	-$(COMPOSE) down --rmi local -v

clean-data: ## Delete all parsed data (irreversible)
	rm -rf data/cars.json data/cars.csv data/images data/raw data/recon data/parser.log data/state.json

clean-profile: ## Forget the browser profile (you will re-do the site check)
	rm -rf data/profile

clean-db: ## Drop the Postgres volume (irreversible)
	-$(COMPOSE) down -v
