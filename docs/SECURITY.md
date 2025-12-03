# 🔒 Security Guide

Security best practices, configuration, and checklist for the Docling API.

---

## Table of Contents

- [Security Overview](#security-overview)
- [Authentication](#authentication)
- [Network Security](#network-security)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Rate Limiting](#rate-limiting)
- [Secrets Management](#secrets-management)
- [Security Checklist](#security-checklist)
- [Incident Response](#incident-response)

---

## Security Overview

### Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Network                                           │
│  ├── Nginx reverse proxy (public facing)                    │
│  ├── Internal Docker network (services isolated)            │
│  └── Flower bound to localhost only                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Transport                                         │
│  ├── TLS 1.2/1.3 only                                       │
│  ├── Strong cipher suites                                   │
│  └── Auto-renewed certificates (Let's Encrypt)              │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Application                                       │
│  ├── API key authentication                                 │
│  ├── Startup security validation                            │
│  ├── Input validation (Pydantic)                            │
│  └── Rate limiting                                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Runtime                                           │
│  ├── Non-root container user                                │
│  ├── Read-only filesystem (where possible)                  │
│  └── Resource limits                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Authentication

### API Key Authentication

All API endpoints require the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-secure-token" https://api.example.com/convert
```

### Generating Secure Tokens

```bash
# Generate 32-byte (64 character) hex token
openssl rand -hex 32

# Or use Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Or use /dev/urandom
head -c 32 /dev/urandom | xxd -p -c 64
```

### Token Requirements

| Environment | Minimum Length | Validation |
|-------------|----------------|------------|
| Production | 16 characters | Enforced at startup |
| Development | Any | Warning only |

**Blocked weak tokens:**
- `changeme`
- `dev-token-123`
- `test`
- `admin`
- `password`
- Empty string

### Startup Validation

The API **will not start** in production with weak credentials:

```python
# This happens automatically in main.py
def _validate_security_settings():
    if env == "production" and token in weak_tokens:
        raise RuntimeError("Weak API token not allowed in production")
```

---

## Network Security

### Service Exposure

| Service | Port | Binding | Accessible From |
|---------|------|---------|-----------------|
| Nginx | 80, 443 | `0.0.0.0` | Public internet |
| API | 8000 | Internal | Docker network only |
| Redis | 6379 | Internal | Docker network only |
| Flower | 5555 | `127.0.0.1` | Localhost only |

### Docker Network Isolation

```yaml
# docker-compose.yml
services:
  nginx:
    ports:
      - "80:80"      # Public
      - "443:443"    # Public
  
  api:
    # No ports exposed - internal only
    networks:
      - docling-network
  
  redis:
    # No ports exposed - internal only
    networks:
      - docling-network
  
  flower:
    ports:
      - "127.0.0.1:5555:5555"  # Localhost only
```

### Accessing Internal Services

**Flower Dashboard (via SSH tunnel):**

```bash
# From your local machine
ssh -L 5555:localhost:5555 user@your-server

# Then open: http://localhost:5555
```

**Redis (for debugging):**

```bash
# Only from server itself
docker compose exec redis redis-cli
```

---

## SSL/TLS Configuration

### Certificate Management

Certificates are automatically managed by Certbot:

```bash
# Check certificate status
make ssl-status

# Manual renewal
make ssl-renew

# View certificate details
openssl x509 -in certbot/conf/live/yourdomain.com/fullchain.pem -text -noout
```

### TLS Configuration

Current settings in `nginx/nginx.conf`:

```nginx
# Protocols - TLS 1.2 and 1.3 only
ssl_protocols TLSv1.2 TLSv1.3;

# Strong cipher suites
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:...;

# Prefer server ciphers
ssl_prefer_server_ciphers off;

# Session settings
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;

# OCSP stapling
ssl_stapling on;
ssl_stapling_verify on;
```

### HSTS (HTTP Strict Transport Security)

Enable after confirming HTTPS works:

```nginx
# Uncomment in nginx.conf after testing
add_header Strict-Transport-Security "max-age=63072000" always;
```

### Testing SSL Configuration

```bash
# Test with SSL Labs
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com

# Local test
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Check certificate chain
curl -vI https://yourdomain.com 2>&1 | grep -A5 "Server certificate"
```

---

## Rate Limiting

### Current Limits (per IP)

| Endpoint | Rate | Burst | Connections |
|----------|------|-------|-------------|
| General API | 30/s | 50 | 50 |
| File uploads | 5/s | 10 | 10 |

### Configuration

In `nginx/nginx.conf`:

```nginx
# Rate limit zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=5r/s;
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

# Apply to endpoints
location / {
    limit_req zone=api_limit burst=50 nodelay;
    limit_conn conn_limit 50;
}

location /convert/upload {
    limit_req zone=upload_limit burst=10 nodelay;
    limit_conn conn_limit 10;
}
```

### Customizing Limits

```nginx
# Higher limits for trusted networks
geo $limit_key {
    default         $binary_remote_addr;
    10.0.0.0/8      "";  # No limit for internal IPs
    192.168.0.0/16  "";
}

limit_req_zone $limit_key zone=api_limit:10m rate=100r/s;
```

### Disabling Rate Limiting

Not recommended, but if needed:

```nginx
# Comment out these lines in location blocks:
# limit_req zone=api_limit burst=50 nodelay;
# limit_conn conn_limit 50;
```

---

## Secrets Management

### Required Secrets

| Secret | Purpose | Generation |
|--------|---------|------------|
| `DOCLING_API_TOKEN` | API authentication | `openssl rand -hex 32` |
| `FLOWER_PASSWORD` | Flower dashboard | `openssl rand -hex 16` |
| `REDIS_PASSWORD` | Redis auth (optional) | `openssl rand -hex 16` |

### Setting Up Secrets

```bash
# Generate all secrets
cat > .env << 'EOF'
DOCLING_API_TOKEN=$(openssl rand -hex 32)
FLOWER_PASSWORD=$(openssl rand -hex 16)
REDIS_PASSWORD=$(openssl rand -hex 16)
ENV=production
EOF

# Secure the file
chmod 600 .env
```

### Secret Rotation

```bash
# 1. Generate new token
NEW_TOKEN=$(openssl rand -hex 32)

# 2. Update .env
sed -i "s/DOCLING_API_TOKEN=.*/DOCLING_API_TOKEN=$NEW_TOKEN/" .env

# 3. Restart services
make restart

# 4. Update clients with new token
```

### What's NOT Stored

- API tokens are not logged
- Passwords are not in error messages
- Internal paths are not exposed to clients

---

## Security Checklist

### Pre-Deployment

```bash
# Run this checklist before going live

# 1. Check API token strength
echo $DOCLING_API_TOKEN | wc -c  # Should be 65+ (32 bytes hex + newline)

# 2. Verify Flower password changed
grep FLOWER_PASSWORD .env  # Should NOT be "admin"

# 3. Check .env permissions
ls -la .env  # Should be -rw------- (600)

# 4. Verify .env is gitignored
git status --ignored | grep .env  # Should show as ignored

# 5. Test SSL certificate
curl -vI https://yourdomain.com 2>&1 | grep "SSL certificate verify ok"

# 6. Verify Flower not public
curl http://yourdomain.com:5555  # Should fail/timeout
```

### Post-Deployment

```bash
# 1. Test authentication required
curl https://yourdomain.com/convert  # Should return 401

# 2. Test rate limiting
for i in {1..100}; do curl -s -o /dev/null -w "%{http_code}\n" \
  https://yourdomain.com/health; done | sort | uniq -c
# Should see some 429 responses

# 3. Check for exposed services
nmap -p 5555,6379,8000 yourdomain.com
# Only 80 and 443 should be open externally
```

### Regular Audits

**Monthly:**
- [ ] Review access logs for anomalies
- [ ] Check SSL certificate expiry
- [ ] Verify rate limiting is working

**Quarterly:**
- [ ] Rotate API tokens
- [ ] Update dependencies
- [ ] Review Docker image vulnerabilities

---

## Incident Response

### Suspected Token Compromise

```bash
# 1. Immediately rotate token
NEW_TOKEN=$(openssl rand -hex 32)
sed -i "s/DOCLING_API_TOKEN=.*/DOCLING_API_TOKEN=$NEW_TOKEN/" .env
make restart

# 2. Review logs for unauthorized access
docker compose logs api | grep -E "(401|403|ERROR)"

# 3. Notify affected users of new token
```

### DDoS/High Traffic

```bash
# 1. Check current connections
docker compose exec nginx sh -c 'netstat -an | grep ESTABLISHED | wc -l'

# 2. Temporarily tighten rate limits
# Edit nginx.conf: rate=5r/s, burst=10
make restart

# 3. Block specific IPs if needed
# Add to nginx.conf:
# deny 1.2.3.4;
```

### Service Compromise

```bash
# 1. Stop services
make down

# 2. Backup current state
tar -czvf incident-backup-$(date +%Y%m%d).tar.gz .

# 3. Review container logs
docker compose logs > incident-logs.txt

# 4. Rebuild from clean images
docker compose build --no-cache
make up
```

---

**Next:** [Configuration Reference](./CONFIGURATION.md) | [Deployment Guide](./DEPLOYMENT.md)
