# ============================================
# Docling Production Makefile
# Domain: docling.ayunis.de
# ============================================

.PHONY: help build up down logs shell ssl-init ssl-renew clean status restart scale \
        dev-build dev-up dev-down dev-logs dev-status dev-restart dev-clean dev-test \
        upgrade upgrade-check upgrade-docling upgrade-dev rollback

# Default target
help:
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║           Docling Production - Management Commands           ║"
	@echo "╠══════════════════════════════════════════════════════════════╣"
	@echo "║  🔧 DEVELOPMENT (No SSL - localhost):                        ║"
	@echo "║    make dev-up        - Start dev environment                ║"
	@echo "║    make dev-build     - Build dev Docker images              ║"
	@echo "║    make dev-down      - Stop dev environment                 ║"
	@echo "║    make dev-logs      - View dev logs (follow)               ║"
	@echo "║    make dev-status    - Show dev service status              ║"
	@echo "║    make dev-restart   - Restart dev services                 ║"
	@echo "║    make dev-test      - Test dev API endpoints               ║"
	@echo "║    make dev-clean     - Clean dev containers & volumes       ║"
	@echo "║                                                              ║"
	@echo "║  🚀 PRODUCTION (SSL enabled):                                ║"
	@echo "║  Setup & SSL:                                                ║"
	@echo "║    make init          - First-time initialization            ║"
	@echo "║    make ssl-init      - Obtain SSL certificate (first time)  ║"
	@echo "║    make ssl-renew     - Manually renew SSL certificate       ║"
	@echo "║    make ssl-staging   - Test with Let's Encrypt staging      ║"
	@echo "║                                                              ║"
	@echo "║  Docker Operations:                                          ║"
	@echo "║    make build         - Build all Docker images              ║"
	@echo "║    make up            - Start all services                   ║"
	@echo "║    make down          - Stop all services                    ║"
	@echo "║    make restart       - Restart all services                 ║"
	@echo "║    make logs          - View all logs (follow)               ║"
	@echo "║    make status        - Show service status                  ║"
	@echo "║                                                              ║"
	@echo "║  Scaling & Monitoring:                                       ║"
	@echo "║    make scale N=3     - Scale workers to N instances         ║"
	@echo "║    make monitoring    - Start with Flower monitoring         ║"
	@echo "║                                                              ║"
	@echo "║  Maintenance:                                                ║"
	@echo "║    make shell-api     - Shell into API container             ║"
	@echo "║    make shell-worker  - Shell into worker container          ║"
	@echo "║    make clean         - Remove all containers and volumes    ║"
	@echo "║    make prune         - Clean up Docker system               ║"
	@echo "║                                                              ║"
	@echo "║  🔄 UPGRADES:                                                 ║"
	@echo "║    make upgrade       - Upgrade all dependencies             ║"
	@echo "║    make upgrade-check - Check for available updates          ║"
	@echo "║    make upgrade-docling - Upgrade Docling only               ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"

# Configuration
DOMAIN := docling.ayunis.de
EMAIL := vineeth.nk@locaboo.com
COMPOSE := docker compose
COMPOSE_FILE := docker-compose.yml

# ============================================
# Initialization
# ============================================

init: check-env build ssl-init up
	@echo "✅ Initialization complete!"
	@echo "🌐 Your Docling API is available at: https://$(DOMAIN)"
	@echo "📚 API Documentation: https://$(DOMAIN)/docs"

check-env:
	@if [ ! -f .env ]; then \
		echo "⚠️  No .env file found. Creating from .env.example..."; \
		cp app/.env.example .env; \
		echo "⚠️  Please edit .env with your settings before continuing."; \
		exit 1; \
	fi

# ============================================
# SSL Certificate Management
# ============================================

ssl-init:
	@echo "🔐 Obtaining SSL certificate for $(DOMAIN)..."
	@mkdir -p certbot/www certbot/conf
	@# Use initial config without SSL first
	@cp nginx/nginx-initial.conf nginx/nginx.conf.bak
	@cp nginx/nginx-initial.conf nginx/nginx.conf
	@$(COMPOSE) up -d nginx api redis
	@sleep 5
	@docker run --rm \
		-v $(PWD)/certbot/www:/var/www/certbot \
		-v $(PWD)/certbot/conf:/etc/letsencrypt \
		certbot/certbot certonly \
		--webroot \
		--webroot-path=/var/www/certbot \
		--email $(EMAIL) \
		--agree-tos \
		--no-eff-email \
		--force-renewal \
		-d $(DOMAIN)
	@# Restore full SSL config
	@mv nginx/nginx.conf.bak nginx/nginx.conf
	@$(COMPOSE) restart nginx
	@echo "✅ SSL certificate obtained successfully!"

ssl-staging:
	@echo "🔐 Testing SSL with Let's Encrypt staging..."
	@mkdir -p certbot/www certbot/conf
	@cp nginx/nginx-initial.conf nginx/nginx.conf.bak
	@cp nginx/nginx-initial.conf nginx/nginx.conf
	@$(COMPOSE) up -d nginx api redis
	@sleep 5
	@docker run --rm \
		-v $(PWD)/certbot/www:/var/www/certbot \
		-v $(PWD)/certbot/conf:/etc/letsencrypt \
		certbot/certbot certonly \
		--webroot \
		--webroot-path=/var/www/certbot \
		--email $(EMAIL) \
		--agree-tos \
		--no-eff-email \
		--staging \
		-d $(DOMAIN)
	@mv nginx/nginx.conf.bak nginx/nginx.conf
	@$(COMPOSE) restart nginx
	@echo "✅ Staging certificate obtained!"

ssl-renew:
	@echo "🔄 Renewing SSL certificate..."
	@docker run --rm \
		-v $(PWD)/certbot/www:/var/www/certbot \
		-v $(PWD)/certbot/conf:/etc/letsencrypt \
		certbot/certbot renew --webroot -w /var/www/certbot
	@$(COMPOSE) exec nginx nginx -s reload
	@echo "✅ SSL certificate renewed!"

# ============================================
# Docker Operations
# ============================================

build:
	@echo "🔨 Building Docker images..."
	@$(COMPOSE) build api
	@echo "✅ Image built: docling-api:latest (used by api, worker, flower)"

up:
	@echo "🚀 Starting services..."
	@$(COMPOSE) up -d
	@echo "✅ Services started!"
	@make status

down:
	@echo "🛑 Stopping services..."
	@$(COMPOSE) down
	@echo "✅ Services stopped!"

restart:
	@echo "🔄 Restarting services..."
	@$(COMPOSE) restart
	@echo "✅ Services restarted!"

logs:
	@$(COMPOSE) logs -f

logs-api:
	@$(COMPOSE) logs -f api

logs-worker:
	@$(COMPOSE) logs -f worker

logs-nginx:
	@$(COMPOSE) logs -f nginx

status:
	@echo "📊 Service Status:"
	@echo "=================="
	@$(COMPOSE) ps
	@echo ""
	@echo "🔗 Endpoints:"
	@echo "  API:     https://$(DOMAIN)"
	@echo "  Docs:    https://$(DOMAIN)/docs"
	@echo "  Health:  https://$(DOMAIN)/health"
	@echo "  Flower:  http://localhost:5555 (localhost only, use SSH tunnel for remote access)"

# ============================================
# Scaling & Monitoring
# ============================================

scale:
ifndef N
	@echo "Usage: make scale N=<number>"
	@echo "Example: make scale N=3"
else
	@echo "📈 Scaling workers to $(N) instances..."
	@$(COMPOSE) up -d --scale worker=$(N)
	@echo "✅ Scaled to $(N) workers!"
endif

monitoring:
	@echo "📊 Starting with Flower monitoring..."
	@$(COMPOSE) --profile monitoring up -d
	@echo "✅ Flower dashboard available at: http://localhost:5555"
	@echo "   🔒 Bound to localhost only (not exposed to public)"
	@echo "   Default credentials: admin/admin"
	@echo ""
	@echo "💡 For remote access, use SSH tunnel:"
	@echo "   ssh -L 5555:localhost:5555 user@your-server"

# ============================================
# Maintenance
# ============================================

shell-api:
	@$(COMPOSE) exec api /bin/bash

shell-worker:
	@$(COMPOSE) exec worker /bin/bash

shell-redis:
	@$(COMPOSE) exec redis redis-cli

clean:
	@echo "🧹 Cleaning up..."
	@$(COMPOSE) down -v --remove-orphans
	@docker system prune -f
	@echo "✅ Cleanup complete!"

prune:
	@echo "🗑️  Pruning Docker system..."
	@docker system prune -af --volumes
	@echo "✅ Prune complete!"

# ============================================
# Development Environment (No SSL)
# ============================================

COMPOSE_DEV := docker compose -f docker-compose.dev.yml
DEV_API_TOKEN := dev-token-123

dev-build:
	@echo "🔨 Building development Docker images..."
	@$(COMPOSE_DEV) build --no-cache api
	@echo "✅ Build complete!"

dev-up: dev-build
	@echo "🔧 Starting development environment..."
	@$(COMPOSE_DEV) up -d
	@echo ""
	@echo "✅ Development environment started!"
	@make dev-status

dev-down:
	@echo "🛑 Stopping development environment..."
	@$(COMPOSE_DEV) down
	@echo "✅ Development environment stopped!"

dev-restart:
	@echo "🔄 Restarting development services..."
	@$(COMPOSE_DEV) restart
	@echo "✅ Development services restarted!"

dev-logs:
	@$(COMPOSE_DEV) logs -f

dev-logs-api:
	@$(COMPOSE_DEV) logs -f api

dev-logs-worker:
	@$(COMPOSE_DEV) logs -f worker

dev-status:
	@echo "📊 Development Service Status:"
	@echo "=============================="
	@$(COMPOSE_DEV) ps
	@echo ""
	@echo "🔗 Development Endpoints:"
	@echo "  API (via nginx):  http://localhost:8080"
	@echo "  API (direct):     http://localhost:8000"
	@echo "  Docs:             http://localhost:8080/docs"
	@echo "  Flower:           http://localhost:5555 (admin/admin)"
	@echo ""
	@echo "🔑 Dev API Token: $(DEV_API_TOKEN)"

dev-clean:
	@echo "🧹 Cleaning development environment..."
	@$(COMPOSE_DEV) down -v --remove-orphans
	@echo "✅ Development cleanup complete!"

dev-shell-api:
	@$(COMPOSE_DEV) exec api /bin/bash

dev-shell-worker:
	@$(COMPOSE_DEV) exec worker /bin/bash

dev-shell-redis:
	@$(COMPOSE_DEV) exec redis redis-cli

dev-test:
	@echo "🧪 Testing development API..."
	@echo ""
	@echo "1️⃣  Health Check:"
	@curl -s http://localhost:8080/health | jq . || echo "❌ API not ready yet"
	@echo ""
	@echo "2️⃣  Health Live:"
	@curl -s http://localhost:8080/health/live | jq . || echo "❌ API not ready yet"
	@echo ""
	@echo "3️⃣  Health Ready:"
	@curl -s http://localhost:8080/health/ready | jq . || echo "❌ API not ready yet"

dev-test-convert:
	@echo "🧪 Testing document conversion (dev)..."
	@curl -s -X POST http://localhost:8080/convert \
		-H "Content-Type: application/json" \
		-H "X-API-Key: $(DEV_API_TOKEN)" \
		-d '{"url": "https://arxiv.org/pdf/2408.09869"}' | jq .

dev-test-upload:
	@echo "📤 Testing file upload (dev)..."
	@echo "Usage: curl -X POST http://localhost:8080/convert/upload \\"
	@echo "  -H 'X-API-Key: $(DEV_API_TOKEN)' \\"
	@echo "  -F 'file=@/path/to/document.pdf'"

# ============================================
# Production Test Helpers
# ============================================

test-api:
	@echo "🧪 Testing API..."
	@curl -s https://$(DOMAIN)/health | jq .

test-convert:
	@echo "🧪 Testing document conversion..."
	@curl -s -X POST https://$(DOMAIN)/convert \
		-H "Content-Type: application/json" \
		-H "X-API-Key: $${DOCLING_API_TOKEN}" \
		-d '{"url": "https://arxiv.org/pdf/2408.09869"}' | jq .

backup-certs:
	@echo "💾 Backing up SSL certificates..."
	@tar -czvf certbot-backup-$$(date +%Y%m%d).tar.gz certbot/
	@echo "✅ Certificates backed up!"

# ============================================
# Quick Commands
# ============================================

# Start everything
start: up

# Stop everything  
stop: down

# View API logs
api: logs-api

# View worker logs
worker: logs-worker

# ============================================
# Upgrade Commands
# ============================================

upgrade-check:
	@echo "🔍 Checking for available updates..."
	@echo ""
	@echo "📦 Current versions:"
	@grep -E "^(docling|docling-core|easyocr|celery|fastapi|flower)" app/requirements.txt || true
	@echo ""
	@echo "📡 Latest versions on PyPI:"
	@echo -n "  docling: " && curl -s https://pypi.org/pypi/docling/json | jq -r '.info.version' 2>/dev/null || echo "unknown"
	@echo -n "  docling-core: " && curl -s https://pypi.org/pypi/docling-core/json | jq -r '.info.version' 2>/dev/null || echo "unknown"
	@echo -n "  fastapi: " && curl -s https://pypi.org/pypi/fastapi/json | jq -r '.info.version' 2>/dev/null || echo "unknown"
	@echo -n "  celery: " && curl -s https://pypi.org/pypi/celery/json | jq -r '.info.version' 2>/dev/null || echo "unknown"
	@echo ""
	@echo "💡 Run 'make upgrade' to upgrade all dependencies"
	@echo "💡 Run 'make upgrade-docling' to upgrade Docling only"

upgrade-docling:
	@echo "⬆️  Upgrading Docling..."
	@echo ""
	@echo "1️⃣  Fetching latest Docling version..."
	@LATEST=$$(curl -s https://pypi.org/pypi/docling/json | jq -r '.info.version') && \
	echo "   Latest version: $$LATEST" && \
	sed -i.bak "s/^docling>=.*/docling>=$$LATEST/" app/requirements.txt && \
	rm -f app/requirements.txt.bak && \
	echo "   Updated requirements.txt"
	@echo ""
	@echo "2️⃣  Rebuilding Docker images..."
	@$(COMPOSE) build --no-cache api
	@echo ""
	@echo "3️⃣  Restarting services..."
	@$(COMPOSE) up -d api worker
	@echo ""
	@echo "✅ Docling upgraded successfully!"
	@echo ""
	@echo "💡 Check logs with: make logs"
	@echo "💡 Test with: make test-api"

upgrade:
	@echo "⬆️  Upgrading all dependencies..."
	@echo ""
	@echo "1️⃣  Updating requirements.txt with latest versions..."
	@# Update Docling
	@DOCLING_VER=$$(curl -s https://pypi.org/pypi/docling/json | jq -r '.info.version') && \
	sed -i.bak "s/^docling>=.*/docling>=$$DOCLING_VER/" app/requirements.txt
	@# Update docling-core
	@DOCLING_CORE_VER=$$(curl -s https://pypi.org/pypi/docling-core/json | jq -r '.info.version') && \
	sed -i.bak "s/^docling-core>=.*/docling-core>=$$DOCLING_CORE_VER/" app/requirements.txt
	@# Update FastAPI
	@FASTAPI_VER=$$(curl -s https://pypi.org/pypi/fastapi/json | jq -r '.info.version') && \
	sed -i.bak "s/^fastapi>=.*/fastapi>=$$FASTAPI_VER/" app/requirements.txt
	@# Update Celery
	@CELERY_VER=$$(curl -s https://pypi.org/pypi/celery/json | jq -r '.info.version') && \
	sed -i.bak "s/^celery\[redis\]>=.*/celery[redis]>=$$CELERY_VER/" app/requirements.txt
	@# Cleanup backup files
	@rm -f app/requirements.txt.bak
	@echo "   ✅ requirements.txt updated"
	@echo ""
	@echo "2️⃣  Pulling latest base images..."
	@docker pull python:3.12-slim
	@docker pull redis:7-alpine
	@docker pull nginx:1.27-alpine
	@echo ""
	@echo "3️⃣  Rebuilding Docker images (this may take a while)..."
	@$(COMPOSE) build --no-cache api
	@echo ""
	@echo "4️⃣  Restarting services..."
	@$(COMPOSE) up -d
	@echo ""
	@echo "✅ All dependencies upgraded successfully!"
	@echo ""
	@echo "📋 Post-upgrade checklist:"
	@echo "   1. Check logs: make logs"
	@echo "   2. Test API: make test-api"
	@echo "   3. Test conversion: make test-convert"
	@echo ""
	@echo "⚠️  If issues occur, restore from backup:"
	@echo "   git checkout app/requirements.txt"
	@echo "   make build && make up"

upgrade-dev:
	@echo "⬆️  Upgrading development environment..."
	@$(COMPOSE_DEV) build --no-cache
	@$(COMPOSE_DEV) up -d
	@echo "✅ Development environment upgraded!"

rollback:
	@echo "⏪ Rolling back to previous version..."
	@git checkout app/requirements.txt
	@$(COMPOSE) build --no-cache api
	@$(COMPOSE) up -d
	@echo "✅ Rollback complete!"
