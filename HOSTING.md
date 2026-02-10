# PaperPlane Hosting Guide ✈️

Step-by-step guide to deploy PaperPlane at `paperplane.harsh.software` with CI/CD.

## Architecture Overview

| Component | Platform | Cost | Subdomain |
|-----------|----------|------|-----------|
| Frontend | Vercel (free) | $0/mo | `paperplane.harsh.software` |
| Backend + DB | DigitalOcean Droplet | $6/mo | `api.paperplane.harsh.software` |
| CI/CD | GitHub Actions (free) | $0/mo | — |

> **Why this split?** The backend needs Playwright + Chromium (headless browser for scraping/filling), which requires a real Linux server with ~1GB RAM. Vercel is free and has native Next.js support with CDN + auto-SSL.

**Estimated monthly cost:** ~$6/mo from your $200 DigitalOcean credit (lasts ~33 months)

---

## Step 1: Create DigitalOcean Droplet

1. Go to [cloud.digitalocean.com](https://cloud.digitalocean.com)
2. **Create Droplet:**
   - **Image:** Ubuntu 24.04 LTS
   - **Plan:** Basic → Regular (SSD) → **$6/mo** (1 vCPU, 1GB RAM, 25GB SSD)
   - **Region:** Choose closest to you (e.g., NYC1)
   - **Authentication:** SSH Key (recommended) or Password
   - **Hostname:** `paperplane`
3. Note the Droplet's **IP address** (e.g., `164.90.xxx.xxx`)

---

## Step 2: DNS Setup on name.com

Go to [name.com](https://www.name.com) → **My Domains** → `harsh.software` → **DNS Records**

Add these records:

| Type | Host | Value | TTL |
|------|------|-------|-----|
| `A` | `api.paperplane` | `YOUR_DROPLET_IP` | 300 |
| `CNAME` | `paperplane` | `cname.vercel-dns.com` | 300 |

> It takes 5-30 minutes for DNS to propagate. Check with: `dig api.paperplane.harsh.software`

---

## Step 3: Set Up the Droplet

SSH into your Droplet:

```bash
ssh root@YOUR_DROPLET_IP
```

### 3.1 Initial Server Setup

```bash
# Update system
apt update && apt upgrade -y

# Create app user
adduser paperplane
usermod -aG sudo paperplane

# Install Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker paperplane

# Install Docker Compose plugin
apt install -y docker-compose-plugin

# Install Nginx (reverse proxy)
apt install -y nginx

# Install Certbot (SSL certificates)
apt install -y certbot python3-certbot-nginx

# Switch to app user
su - paperplane
```

### 3.2 Clone and Configure the Project

```bash
# Clone your repo
git clone https://github.com/Harsh-H-Shah/PaperPlane.git
cd PaperPlane

# Create production .env
cp .env.example .env
nano .env
```

Edit `.env` with your production values:

```ini
# PaperPlane Environment Configuration
GEMINI_API_KEY=your_actual_key
DISCORD_WEBHOOK_URL=your_webhook
HEADLESS=true
AUTO_SUBMIT=false
MAX_APPLICATIONS_PER_RUN=10
```

### 3.3 Start the Backend

```bash
# Build and start (only the backend — frontend goes to Vercel)
docker compose up -d backend

# Verify it's running
docker compose logs -f backend
# Should see: "🚀 Starting PaperPlane API at http://0.0.0.0:8080"

# Test the API
curl http://localhost:8080/api/stats
```

### 3.4 Configure Nginx Reverse Proxy

```bash
# As root user
sudo nano /etc/nginx/sites-available/paperplane-api
```

Paste this config:

```nginx
server {
    server_name api.paperplane.harsh.software;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Longer timeouts for scraping operations
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

Enable and activate:

```bash
sudo ln -s /etc/nginx/sites-available/paperplane-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3.5 SSL Certificate (HTTPS)

```bash
sudo certbot --nginx -d api.paperplane.harsh.software
# Follow the prompts. Choose to redirect HTTP → HTTPS.

# Auto-renewal is set up automatically. Verify:
sudo certbot renew --dry-run
```

### 3.6 Auto-Restart on Reboot

```bash
# Docker containers restart automatically (restart: unless-stopped in docker-compose.yml)
# But ensure Docker starts on boot:
sudo systemctl enable docker
```

---

## Step 4: Deploy Frontend to Vercel

### 4.1 Connect to Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import your GitHub repository
3. **Framework Preset:** Next.js
4. **Root Directory:** `frontend`
5. **Environment Variables:**

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://api.paperplane.harsh.software` |

6. Click **Deploy**

### 4.2 Add Custom Domain

1. In Vercel project → **Settings** → **Domains**
2. Add: `paperplane.harsh.software`
3. Vercel will show you the DNS values — you already added the CNAME record in Step 2
4. SSL is automatic on Vercel

---

## Step 5: Set Up CI/CD

### 5.1 GitHub Secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions**

Add these secrets:

| Secret | Value |
|--------|-------|
| `DROPLET_IP` | Your Droplet IP address |
| `SSH_PRIVATE_KEY` | Your SSH private key (for the `paperplane` user) |
| `VERCEL_TOKEN` | Get from [vercel.com/account/tokens](https://vercel.com/account/tokens) |
| `VERCEL_ORG_ID` | From `.vercel/project.json` after first deploy |
| `VERCEL_PROJECT_ID` | From `.vercel/project.json` after first deploy |

### 5.2 Set Up SSH Key for Deployment

On your **local machine**:

```bash
# Generate a deploy key
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/paperplane_deploy

# Copy public key to Droplet
ssh-copy-id -i ~/.ssh/paperplane_deploy.pub paperplane@YOUR_DROPLET_IP

# Copy private key content — paste into GitHub Secrets as SSH_PRIVATE_KEY
cat ~/.ssh/paperplane_deploy
```

### 5.3 How It Works

Every push to `main`:
1. **Test job:** Lints backend (ruff) + builds frontend
2. **Deploy backend:** SSHs into Droplet → `git pull` → `docker compose up -d --build backend`
3. **Deploy frontend:** Pushes to Vercel via their API

The workflow is at `.github/workflows/deploy.yml`.

---

## Step 6: Environment Variables Checklist

### On DigitalOcean (`.env` file on the Droplet)

```bash
# SSH in and edit
ssh paperplane@YOUR_DROPLET_IP
cd PaperPlane
nano .env
```

All backend env vars go here (Gemini key, Discord webhook, LinkedIn cookies, etc.)

### On Vercel (Web UI)

Only one variable needed:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://api.paperplane.harsh.software` |

---

## Step 7: Monitoring & Maintenance

### View Logs

```bash
# Backend logs
ssh paperplane@YOUR_DROPLET_IP
cd PaperPlane
docker compose logs -f backend --tail 100

# Application logs
cat logs/activity.log
```

### Restart Services

```bash
docker compose restart backend
```

### Update Manually (if CI/CD is not set up yet)

```bash
ssh paperplane@YOUR_DROPLET_IP
cd PaperPlane
git pull origin main
docker compose up -d --build backend
```

### Backups

```bash
# Backup the database (run from Droplet)
cp data/applications.db data/applications.db.backup.$(date +%Y%m%d)

# Or download to local
scp paperplane@YOUR_DROPLET_IP:~/PaperPlane/data/applications.db ./backup/
```

### Resource Monitoring

```bash
# Check Docker resource usage
docker stats

# Check disk space
df -h

# Check memory
free -h
```

---

## Quick Reference

| What | URL |
|------|-----|
| Frontend Dashboard | `https://paperplane.harsh.software` |
| Backend API | `https://api.paperplane.harsh.software` |
| API Docs (Swagger) | `https://api.paperplane.harsh.software/docs` |
| Vercel Dashboard | `https://vercel.com/dashboard` |
| DigitalOcean Console | `https://cloud.digitalocean.com` |
| GitHub Actions | `https://github.com/Harsh-H-Shah/PaperPlane/actions` |

---

## Troubleshooting

**502 Bad Gateway from Nginx**
→ Backend container isn't running. Check: `docker compose ps` and `docker compose logs backend`

**SSL certificate issues**
→ Re-run: `sudo certbot --nginx -d api.paperplane.harsh.software`

**Frontend can't reach backend (CORS error)**
→ The backend CORS config already includes `https://paperplane.harsh.software`. If using a different domain, update `backend/src/dashboard/app.py`.

**Out of memory on Droplet**
→ Playwright + Chromium uses ~300-500MB. If the $6 Droplet isn't enough, upgrade to $12/mo (2GB RAM) — still well within your $200 credit.

**Docker build fails on Droplet**
→ The $6 Droplet has limited RAM. Try: `docker compose build --no-cache backend` or add swap:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```
