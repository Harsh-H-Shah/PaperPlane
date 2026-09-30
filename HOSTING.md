# Hosting PaperPlane

| Part | Where | Address | Cost |
| --- | --- | --- | --- |
| Frontend | GitHub Pages (static export) | `https://paperplane.harshsh.com` | $0 |
| Backend + SQLite | Google Cloud `e2-micro` VM, Always Free | `https://paperplane-api.harshsh.com` | $0 |
| HTTPS for the API | Caddy on the VM (Let's Encrypt, auto-renewing) | — | $0 |
| Deploys | GitHub Actions on every push to `main` | — | $0 |

The backend image is built by GitHub Actions and pulled from GHCR, so the 1 GB VM never compiles anything. Runtime data (`data/`, `.env`) lives only on the VM and is never overwritten by deploys.

---

## 1. Google Cloud VM (one time)

1. Sign up at [console.cloud.google.com](https://console.cloud.google.com) and create a project (e.g. `paperplane`). A billing account is required even for Always Free resources.
2. **Billing → Budgets & alerts:** create a **$1** budget with email alerts. You'll hear about any charge immediately.
3. **Compute Engine → VM instances → Create instance.** Every setting below matters for staying free:
   - **Region:** `us-west1`, `us-central1` or `us-east1` (only these are free)
   - **Machine type:** `e2-micro`
   - **Boot disk:** Ubuntu 24.04 LTS (x86/64), **Standard persistent disk** (not "Balanced"), 30 GB
   - **Firewall:** tick *Allow HTTP traffic* and *Allow HTTPS traffic*
4. **VPC network → IP addresses:** find the VM's external IP and click **Promote to static**, so it survives a stop/start.
5. After 1–2 days, open **Billing → Reports** and confirm the charges are $0.

## 2. Deploy key (on your laptop)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/paperplane_deploy -N "" -C "<vm-username>"
cat ~/.ssh/paperplane_deploy.pub
```

In **Compute Engine → your VM → Edit → SSH Keys**, add the `.pub` contents. The username in the comment becomes your VM login.

```bash
ssh -i ~/.ssh/paperplane_deploy <vm-username>@<VM_IP>
```

## 3. Set up the VM

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

## 4. DNS (Cloudflare, `harshsh.com`)

| Type | Name | Target | Proxy |
| --- | --- | --- | --- |
| `A` | `paperplane-api` | `<VM_IP>` | **DNS only** (grey cloud) |
| `CNAME` | `paperplane` | `harsh-h-shah.github.io` | **DNS only** (grey cloud) |

Keep both grey. Caddy and GitHub Pages each need direct traffic to issue their HTTPS certificates. The API uses a single-level subdomain (`paperplane-api`, not `api.paperplane`) so it stays compatible if you ever turn Cloudflare's proxy on.

## 5. GitHub settings

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

## What recovers on its own

| Event | Automatic? |
| --- | --- |
| Backend crashes | ✅ Docker restarts it (`restart: unless-stopped`) |
| VM reboots (Google maintenance) | ✅ Docker starts on boot and brings both containers back |
| HTTPS certificates | ✅ Caddy (API) and GitHub Pages (frontend) renew them |
| New code on `main` | ✅ GitHub Actions builds, pushes, pulls and health-checks |
| Disk full, DB corrupted, Gemini quota used up | ❌ Needs you. A free uptime monitor (e.g. UptimeRobot on `/api/stats`) will tell you. |

## Day-to-day

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
