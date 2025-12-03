# 🚀 Production Deployment Guide

Complete guide for deploying Docling API to production with SSL, monitoring, and scaling.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Deployment](#quick-deployment)
- [Step-by-Step Deployment](#step-by-step-deployment)
- [SSL Certificate Setup](#ssl-certificate-setup)
- [Monitoring Setup](#monitoring-setup)
- [Scaling Workers](#scaling-workers)
- [Updating & Maintenance](#updating--maintenance)
- [Backup & Recovery](#backup--recovery)
- [Production Checklist](#production-checklist)

---

## Prerequisites

### Server Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 20 GB | 50+ GB |
| OS | Ubuntu 20.04+ / Debian 11+ | Ubuntu 22.04 LTS |

### Software Requirements

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose v2
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Verify installation
docker --version        # Docker version 24.0+
docker compose version  # Docker Compose version v2.20+
```

### Domain Configuration

Point your domain to your server's IP:

```
Type: A
Name: docling (or your subdomain)
Value: YOUR_SERVER_IP
TTL: 300
```

Verify DNS propagation:
```bash
dig docling.yourdomain.com +short
# Should return your server IP
```

---

## Quick Deployment

For experienced users - deploy in 5 minutes:

```bash
# 1. Clone and configure
cd /opt
git clone https://github.com/your-repo/docling-production-setup.git
cd docling-production-setup

# 2. Generate secure credentials
cat > .env << EOF
DOCLING_API_TOKEN=$(openssl rand -hex 32)
FLOWER_PASSWORD=$(openssl rand -hex 16)
REDIS_PASSWORD=$(openssl rand -hex 16)
ENV=production
DOMAIN=docling.yourdomain.com
LETSENCRYPT_EMAIL=admin@yourdomain.com
EOF

# 3. Deploy
make init

# 4. Verify
curl https://docling.yourdomain.com/health
```

---

## Step-by-Step Deployment

### Step 1: Clone the Repository

```bash
# Choose installation directory
sudo mkdir -p /opt/docling
sudo chown $USER:$USER /opt/docling
cd /opt/docling

# Clone repository
git clone https://github.com/your-repo/docling-production-setup.git .
```

### Step 2: Configure Environment

```bash
# Copy example configuration
cp app/.env.example .env

# Generate secure API token (REQUIRED)
export API_TOKEN=$(openssl rand -hex 32)
echo "Generated API Token: $API_TOKEN"

# Generate secure Flower password
export FLOWER_PASS=$(openssl rand -hex 16)

# Generate Redis password
export REDIS_PASS=$(openssl rand -hex 16)

# Edit configuration
nano .env
```

**Required `.env` settings:**

```bash
# ===========================================
# REQUIRED - Change these values!
# ===========================================
DOCLING_API_TOKEN=your-generated-token-here
FLOWER_PASSWORD=your-flower-password-here
REDIS_PASSWORD=your-redis-password-here

# ===========================================
# Domain Configuration
# ===========================================
ENV=production
DOMAIN=docling.yourdomain.com
LETSENCRYPT_EMAIL=admin@yourdomain.com
CORS_ORIGINS=https://docling.yourdomain.com

# ===========================================
# Performance (adjust based on server specs)
# ===========================================
WORKERS=2              # API workers (1 per CPU core)
CELERY_CONCURRENCY=2   # Tasks per worker
```

### Step 3: Build Docker Images

```bash
# Build all images
make build

# Verify images
docker images | grep docling
# Expected output:
# docling-api    latest    abc123...    1 minute ago    2.5GB
```

### Step 4: Obtain SSL Certificate

```bash
# Test with staging certificate first (recommended)
make ssl-staging

# If staging succeeds, get production certificate
make ssl-init

# Verify certificate
make ssl-status
```

### Step 5: Start Services

```bash
# Start all services
make up

# Check status
make status

# View logs
make logs
```

### Step 6: Verify Deployment

```bash
# Health check
curl https://docling.yourdomain.com/health
# Expected: {"status":"healthy","version":"1.0.0",...}

# Test API (replace with your token)
curl -X POST https://docling.yourdomain.com/convert \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-token" \
  -d '{"url": "https://arxiv.org/pdf/2408.09869"}'

# Check task status
curl https://docling.yourdomain.com/tasks/TASK_ID \
  -H "X-API-Key: your-api-token"
```

---

## SSL Certificate Setup

### Initial Setup (Let's Encrypt)

```bash
# 1. Ensure domain points to server
dig docling.yourdomain.com +short

# 2. Open required ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 3. Get certificate
make ssl-init
```

### Certificate Renewal

Certificates auto-renew via the certbot container. For manual renewal:

```bash
# Check certificate expiry
make ssl-status

# Manual renewal
make ssl-renew

# Force renewal (if needed)
docker compose exec certbot certbot renew --force-renewal
make restart
```

### Troubleshooting SSL

```bash
# View certbot logs
docker compose logs certbot

# Test certificate
openssl s_client -connect docling.yourdomain.com:443 -servername docling.yourdomain.com

# Check nginx SSL config
docker compose exec nginx nginx -t
```

---

## Monitoring Setup

### Enable Flower Dashboard

```bash
# Start with monitoring profile
make monitoring

# Access Flower (localhost only for security)
# Option 1: SSH tunnel from your local machine
ssh -L 5555:localhost:5555 user@your-server

# Then open in browser: http://localhost:5555
# Credentials: admin / your-flower-password
```

### Prometheus Metrics

Metrics are available at `/metrics`:

```bash
# View metrics
curl https://docling.yourdomain.com/metrics \
  -H "X-API-Key: your-api-token"

# Example Prometheus scrape config
# prometheus.yml:
scrape_configs:
  - job_name: 'docling'
    static_configs:
      - targets: ['docling.yourdomain.com:443']
    scheme: https
    bearer_token: 'your-api-token'
    metrics_path: '/metrics'
```

### Health Checks

```bash
# Full health status
curl https://docling.yourdomain.com/health

# Kubernetes-style probes
curl https://docling.yourdomain.com/health/live   # Liveness
curl https://docling.yourdomain.com/health/ready  # Readiness
```

---

## Scaling Workers

### Horizontal Scaling (More Workers)

```bash
# Scale to 3 workers
make scale N=3

# Check worker status
docker compose ps | grep worker

# View worker logs
docker compose logs -f worker worker-2 worker-3
```

### Vertical Scaling (More Concurrency)

Edit `.env`:
```bash
# Increase tasks per worker
CELERY_CONCURRENCY=4
```

Then restart:
```bash
make restart
```

### Resource Allocation

Edit `docker-compose.yml` for memory limits:

```yaml
worker:
  deploy:
    resources:
      limits:
        memory: 8G      # Increase for large documents
      reservations:
        memory: 2G
```

### Scaling Recommendations

| Documents/Hour | Workers | Concurrency | RAM |
|----------------|---------|-------------|-----|
| < 50 | 1 | 2 | 4 GB |
| 50-200 | 2 | 2 | 8 GB |
| 200-500 | 3-4 | 2 | 16 GB |
| 500+ | 4+ | 4 | 32 GB |

---

## Updating & Maintenance

### Update Application Code

```bash
# Pull latest changes
git pull origin main

# Rebuild images
make build

# Rolling restart (zero downtime)
docker compose up -d --no-deps api
docker compose up -d --no-deps worker

# Or full restart
make restart
```

### Upgrade Dependencies (Docling, FastAPI, etc.)

```bash
# Check for available updates
make upgrade-check

# Output:
# 📦 Current versions:
#   docling>=2.14.0
#   fastapi>=0.115.5
#   celery[redis]>=5.4.0
#
# 📡 Latest versions on PyPI:
#   docling: 2.15.0
#   fastapi: 0.115.6
#   celery: 5.4.1
```

**Upgrade Docling only:**

```bash
make upgrade-docling
```

**Upgrade all dependencies:**

```bash
make upgrade
```

This will:
1. Update `requirements.txt` with latest versions
2. Pull latest Docker base images
3. Rebuild all containers
4. Restart services

**Rollback if issues occur:**

```bash
make rollback
```

### Manual Dependency Update

If you prefer manual control:

```bash
# 1. Edit requirements.txt
nano app/requirements.txt

# 2. Rebuild images
make build

# 3. Restart services
make restart

# 4. Verify
make test-api
```

### View Logs

```bash
# All services
make logs

# Specific service
make logs-api
make logs-worker

# Last 100 lines
docker compose logs --tail=100 api

# Search logs
docker compose logs api 2>&1 | grep ERROR
```

---

## Backup & Recovery

### Backup Certificates

```bash
# Backup SSL certificates
make backup-certs
# Creates: certbot-backup-YYYYMMDD.tar.gz

# Manual backup
tar -czvf ssl-backup.tar.gz certbot/conf/
```

### Backup Redis Data

```bash
# Create Redis snapshot
docker compose exec redis redis-cli BGSAVE

# Copy snapshot
docker cp docling-redis:/data/dump.rdb ./redis-backup.rdb
```

### Restore from Backup

```bash
# Restore SSL certificates
tar -xzvf certbot-backup-YYYYMMDD.tar.gz

# Restore Redis
docker compose down
docker cp ./redis-backup.rdb docling-redis:/data/dump.rdb
docker compose up -d
```

---

## Production Checklist

### Before Going Live

- [ ] **Security**
  - [ ] Generated secure API token (32+ chars)
  - [ ] Changed Flower password from default
  - [ ] Set Redis password
  - [ ] Verified Flower is localhost-only

- [ ] **SSL/Domain**
  - [ ] Domain DNS points to server
  - [ ] SSL certificate obtained (not staging)
  - [ ] HTTPS redirect working
  - [ ] Certificate auto-renewal configured

- [ ] **Performance**
  - [ ] Adjusted worker count for expected load
  - [ ] Set appropriate memory limits
  - [ ] Tested with sample documents

- [ ] **Monitoring**
  - [ ] Health endpoint responding
  - [ ] Flower dashboard accessible (via SSH tunnel)
  - [ ] Log aggregation configured (optional)

- [ ] **Backup**
  - [ ] SSL certificates backed up
  - [ ] Backup schedule configured

### Post-Deployment Verification

```bash
# Run all checks
make status
curl -s https://yourdomain.com/health | jq .

# Test document conversion
curl -X POST https://yourdomain.com/convert \
  -H "X-API-Key: your-token" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/sample.pdf"}' | jq .

# Check worker processing
docker compose logs -f worker
```

---

## Common Issues

### Services Won't Start

```bash
# Check for port conflicts
sudo netstat -tlnp | grep -E ':(80|443|6379) '

# Check Docker logs
docker compose logs

# Verify .env file
cat .env | grep -v '^#' | grep -v '^$'
```

### SSL Certificate Failed

```bash
# Verify domain resolves
dig yourdomain.com +short

# Check ports are open
curl -v http://yourdomain.com/.well-known/acme-challenge/test

# Use staging first
make ssl-staging
```

### Workers Not Processing

```bash
# Check Redis connection
docker compose exec worker python -c "
import redis
r = redis.from_url('redis://redis:6379')
print('Redis ping:', r.ping())
"

# Check Celery status
docker compose exec worker celery -A worker.celery_app inspect active
```

---

**Next:** [Security Guide](./SECURITY.md) | [Configuration Reference](./CONFIGURATION.md)
