# Hosting PaperPlane

The frontend always lives on **GitHub Pages** at `https://paperplane.harshsh.com` ($0). The backend runs in one of two places, and the API address stays `https://paperplane-api.harshsh.com` either way:

| Backend option | Cost | Up when | Status |
| --- | --- | --- | --- |
| **A. Home server + Cloudflare Tunnel** | $0 | This computer is on and awake | **Current** |
| B. Google Cloud `e2-micro` VM | ~$3.65/mo (public IPv4) | Always | For later |

Runtime data (`data/`, `.env`) never leaves the machine running the backend and is never overwritten by deploys.

---

## A. Home server + Cloudflare Tunnel (current)

The backend runs in Docker on this computer. The tunnel container makes an **outbound** connection to Cloudflare, so there are no open ports or router changes, and Cloudflare provides HTTPS. Both containers restart on their own after a crash, a network drop or a reboot (Docker starts on boot).

### A1. Create the tunnel (Cloudflare dashboard, one time)

1. **Zero Trust → Networks → Tunnels → Create a tunnel →** type **Cloudflared**, name it `paperplane`.
2. On the install screen, **skip the install commands**. Copy the **token** only: the long string after `--token`.
3. **Public hostnames → Add a public hostname:**
   - Subdomain `paperplane-api`, domain `harshsh.com`
   - Service type **HTTP**, URL **`backend:8080`**
   - Cloudflare creates the DNS record for you.

### A2. Start it (on this computer)

Add the token to `.env` (never commit it), then start:

```bash
echo 'TUNNEL_TOKEN=<paste token>' >> .env
docker compose -f docker-compose.tunnel.yml up -d --build
curl https://paperplane-api.harshsh.com/api/stats
```

After pulling new code, run the same `up -d --build` command to rebuild the backend.

### A3. Frontend on GitHub Pages (one time)

- **Cloudflare DNS:** `CNAME` `paperplane` → `harsh-h-shah.github.io`, **DNS only** (grey cloud).
- **GitHub → Settings → Pages:** source **GitHub Actions**, custom domain `paperplane.harshsh.com`, then **Enforce HTTPS** once the certificate is ready.
- **GitHub → Settings → Secrets and variables → Actions → Variables:** `API_URL` = `https://paperplane-api.harshsh.com`.
- Leave `VM_HOST` unset, so the workflow deploys only the frontend.

### A4. Daily jobs (optional)

`crontab -e`, then add (adjust the path):

```cron
0 3 * * * cd $HOME/Desktop/Projects/PaperPlane && COMPOSE_FILE=docker-compose.tunnel.yml ./deploy/backup-db.sh >> logs/backup.log 2>&1
0 9 * * * cd $HOME/Desktop/Projects/PaperPlane && docker compose -f docker-compose.tunnel.yml exec -T backend python main.py scrape --limit 50 >> logs/cron-scrape.log 2>&1
```

### Keep in mind

- **Sleep = offline.** If the computer sleeps, the site shows no data until it wakes. On a laptop, disable suspend while plugged in (Settings → Power), or keep it on AC with the lid-close action set to "do nothing".
- **Reconnection is automatic:** when the network comes back, `cloudflared` reconnects on its own. After a reboot, Docker restarts both containers.
- **Outage alerts:** a free uptime monitor (e.g. UptimeRobot on `https://paperplane-api.harshsh.com/api/stats`) tells you when it's down.

---

## B. Google Cloud VM (for later)

The backend image is built by GitHub Actions and pulled from GHCR, so the 1 GB VM never compiles anything. Setting the `VM_HOST` variable turns this path on.

| Part | Where | Cost |
| --- | --- | --- |
| Backend + SQLite | Google Cloud `e2-micro` VM (Always Free tier) | ~$3.65/mo (public IPv4 only) |
| HTTPS for the API | Caddy on the VM (Let's Encrypt, auto-renewing) | $0 |

### 1. Google Cloud VM (one time)

**Cost:** the VM, a 30 GB standard disk and 1 GB/month of outbound traffic are Always Free. The public IPv4 address is **not** in the free tier. Google charges $0.005/hour for an in-use IPv4 address (about $3.65/month), and the new-account trial credit covers it at first.

The *Create instance* page always shows **list prices** (about $7/month). It doesn't subtract the free tier, which appears as a credit on the bill. What matters is that the settings below match the free tier exactly.

1. Sign up at [console.cloud.google.com](https://console.cloud.google.com) and create a project (e.g. `paperplane`). A billing account is required even for Always Free resources.
2. **Billing → Budgets & alerts:** create a **$5** budget with email alerts, so any unexpected charge beyond the IP address gets flagged.
3. **Compute Engine → VM instances → Create instance.** Every setting below matters:
   - **Region:** `us-west1`, `us-central1` or `us-east1` (only these are free)
   - **Machine type:** series E2, preset **`e2-micro`** (not a *custom* machine type)
   - **Boot disk:** Ubuntu 24.04 LTS (x86/64), change the type from "Balanced" to **Standard persistent disk**, size **30 GB**. Balanced disks are not free.
   - **Data protection / snapshot schedule:** choose **No backups**. Snapshots are billed; `deploy/backup-db.sh` backs up the DB instead.
   - **Networking → network service tier:** keep **Premium** (the default). The free 1 GB of outbound traffic doesn't apply to Standard tier.
   - **Observability / Ops Agent:** leave it off.
   - **Firewall:** tick *Allow HTTP traffic* and *Allow HTTPS traffic*
4. **VPC network → IP addresses:** find the VM's external IP and click **Promote to static**, so it survives a stop/start. It costs the same while attached. If you ever delete the VM, **release the static IP too**, because an unattached one is billed at twice the rate.
5. After 1–2 days, open **Billing → Reports**, group by SKU, and confirm the only charge is the external IP address.

### 2. Deploy key (on your laptop)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/paperplane_deploy -N "" -C "<vm-username>"
cat ~/.ssh/paperplane_deploy.pub
```

In **Compute Engine → your VM → Edit → SSH Keys**, add the `.pub` contents. The username in the comment becomes your VM login.

```bash
ssh -i ~/.ssh/paperplane_deploy <vm-username>@<VM_IP>
```

### 3. Set up the VM

On the VM:

```bash
curl -fsSL https://raw.githubusercontent.com/Harsh-H-Shah/PaperPlane/main/deploy/gcp-setup.sh | bash
exit   # log back in so docker works without sudo
```

The script is safe to re-run. It:

- adds 2 GB of swap;
- installs Docker (starts on boot);
- clones the repo to `~/paperplane`;
- creates `.env` from the template;
- installs two daily cron jobs: a DB backup at 07:00 UTC and a scrape at 13:00 UTC.

From your laptop, copy your data up:

```bash
scp -i ~/.ssh/paperplane_deploy data/applications.db data/profile.json <vm-username>@<VM_IP>:~/paperplane/data/
scp -i ~/.ssh/paperplane_deploy data/Harsh_Shah.pdf <vm-username>@<VM_IP>:~/paperplane/data/resume.pdf
```

Back on the VM, fill in secrets, then start:

```bash
cd ~/paperplane
nano .env        # GEMINI_API_KEY, ADMIN_TOKEN (long random string: openssl rand -hex 32)
chmod 666 data/*  # the container user must be able to write the DB
```

The first start happens on the first deploy (step 5), because the VM needs the image from GHCR.

### 4. DNS (Cloudflare, `harshsh.com`)

| Type | Name | Target | Proxy |
| --- | --- | --- | --- |
| `A` | `paperplane-api` | `<VM_IP>` | **DNS only** (grey cloud) |
| `CNAME` | `paperplane` | `harsh-h-shah.github.io` | **DNS only** (grey cloud) |

Keep both grey. Caddy and GitHub Pages each need direct traffic to issue their HTTPS certificates. The API uses a single-level subdomain (`paperplane-api`, not `api.paperplane`) so it stays compatible if you ever turn Cloudflare's proxy on.

### 5. GitHub settings

**Settings → Pages:**

- Source: **GitHub Actions**
- Custom domain: `paperplane.harshsh.com`
- Tick **Enforce HTTPS** once the certificate is ready

**Settings → Secrets and variables → Actions:**

| Kind | Name | Value |
| --- | --- | --- |
| Variable | `API_URL` | `https://paperplane-api.harshsh.com` |
| Variable | `VM_HOST` | the VM's static IP |
| Variable | `VM_USER` | your VM username |
| Secret | `SSH_PRIVATE_KEY` | contents of `~/.ssh/paperplane_deploy` |

Delete the old `DROPLET_IP`, `VERCEL_TOKEN`, `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` secrets.

Then run **Actions → Deploy PaperPlane → Run workflow** (or push to `main`). Each deploy job only runs when its variable is set: `API_URL` enables the frontend, and `VM_HOST` enables the backend.

Check it:

```bash
curl https://paperplane-api.harshsh.com/api/stats
```

Then open `https://paperplane.harshsh.com`.

---

### What recovers on its own

| Event | Automatic? |
| --- | --- |
| Backend crashes | ✅ Docker restarts it (`restart: unless-stopped`) |
| VM reboots (Google maintenance) | ✅ Docker starts on boot and brings both containers back |
| HTTPS certificates | ✅ Caddy (API) and GitHub Pages (frontend) renew them |
| New code on `main` | ✅ GitHub Actions builds, pushes, pulls and health-checks |
| Disk full, DB corrupted, Gemini quota used up | ❌ Needs you. A free uptime monitor (e.g. UptimeRobot on `/api/stats`) will tell you. |

### Day-to-day

```bash
cd ~/paperplane
docker compose -f docker-compose.prod.yml logs -f backend   # logs
docker compose -f docker-compose.prod.yml restart backend    # restart
ls data/backups/                                             # last 14 nightly DB backups
tail logs/cron-scrape.log                                    # daily scrape output
```

**Restore a backup:** stop the backend, copy `data/backups/applications-YYYY-MM-DD.db` over `data/applications.db`, then start it again.

**Limits to keep in mind:**

- **1 GB RAM:** one browser session at a time, and the swap file absorbs spikes.
- **1 GB/month outbound traffic:** fine for dashboard traffic. Scraping is mostly inbound, which is free.

## Local development

Unchanged: `cd backend && python main.py dashboard`, and `cd frontend && npm run dev`. The original `docker-compose.yml` still builds both services locally.
