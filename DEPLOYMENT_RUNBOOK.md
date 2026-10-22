# VPS Deployment Runbook

This runbook documents a fresh LifeOS deployment on Ubuntu and a repeatable update process. It covers SSH, Docker/Compose, host PostgreSQL, domains/DNS, Nginx, TLS, production secrets, Git branches, and troubleshooting.

## Example values

Replace examples with your actual values:

| Item | Example |
|---|---|
| VPS public IPv4 | `YOUR_VPS_PUBLIC_IP` |
| App hostname | `lifeos.example.in` |
| Repository directory | `/opt/lifeos` |
| Deploy branch | `main` |
| PostgreSQL database/role | `lifeos` |
| Frontend host port | `127.0.0.1:8080` |

For the LifeOS VPS configured in this conversation, the actual hostname is `lifeos.crasenimpharma.in` and the checkout path shown in the SSH session is `/root/lifeos/LifeOS`. Examples below use `/opt/lifeos` and `lifeos.example.in` for a new server; substitute the actual path/domain on an existing server.

LifeOS production Compose runs the API and static frontend in Docker. PostgreSQL and public Nginx run on the VPS host. The frontend container is only reachable through `127.0.0.1:8080`; host Nginx handles public HTTP/HTTPS. Use a subdomain if the root domain hosts a different website.

> **Environment file location:** `.env.production` belongs in the repository root beside `docker-compose.prod.yml`, not inside `backend/` or `frontend/`. Never commit it.

## 1. Prepare access and configuration

Collect the VPS public IP, domain/subdomain, Git URL and deploy branch, Auth0 tenant domain/client ID/API Identifier, SMTP settings, and a PostgreSQL role password. LifeOS production requires an SMTP host. Generate a URL-safe DB password with `openssl rand -hex 24`.

## 2. SSH into Ubuntu

Run this on your own computer (PowerShell/Windows Terminal, macOS Terminal, etc.), not inside another SSH session:

```bash
ssh root@YOUR_VPS_PUBLIC_IP
```

Or use the account/key provided by your VPS host:

```bash
ssh -i PATH_TO_PRIVATE_KEY ubuntu@YOUR_VPS_PUBLIC_IP
```

If you need to create an SSH key on Windows, run this locally in PowerShell, then add the contents of the `.pub` file to the VPS provider's authorized SSH keys. Keep the private key file private:

```powershell
ssh-keygen -t ed25519 -C "lifeos-vps"
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

Replace `ubuntu` with your account name. Verify the host fingerprint with the provider on first connection. Never share the private key. If logged in as a non-root user, prefix system commands below with `sudo`.

```bash
whoami
lsb_release -a
```

The remaining steps assume Ubuntu 22.04 or newer.

## 3. Install/update base packages

```bash
apt-get update
apt-get upgrade -y
apt-get install -y ca-certificates curl git nginx postgresql postgresql-contrib ufw
```

If services are already installed, this keeps the installed package. Check versions/services:

```bash
docker --version
docker compose version
psql --version
nginx -v
systemctl status postgresql --no-pager
systemctl status nginx --no-pager
```

If Docker works but `docker compose version` fails, install Compose v2 below; do not reinstall a working Docker Engine just to add Compose.

## 4. Install Docker Engine and Compose v2

Skip if Docker and `docker compose` already work. Add Docker's official Ubuntu APT repository:

```bash
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
```

```bash
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

Install and enable:

```bash
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker --version
docker compose version
```

If Docker came from Ubuntu's own archive, first check its Compose package rather than switching package sources blindly:

```bash
apt-cache policy docker-compose-v2 docker-compose-plugin
```

Install a supported Compose v2 package and verify it. Don't remove Docker packages or delete `/var/lib/docker` as troubleshooting; existing containers/data may be affected. References: [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/) and [Compose plugin](https://docs.docker.com/compose/install/linux/).

## 5. Firewall

Allow SSH before enabling UFW so you don't lock yourself out. Allow HTTP/HTTPS only; PostgreSQL and the container frontend port should not be public:

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw status
ufw enable
ufw status verbose
```

Also allow TCP 80 and 443 in the VPS provider firewall. Don't expose 5432 or 8080.

## 6. Create PostgreSQL role/database

```bash
systemctl status postgresql --no-pager
openssl rand -hex 24
sudo -u postgres psql
```

At `postgres=#`, replace the placeholder with the generated password, then exit:

```sql
CREATE ROLE lifeos LOGIN PASSWORD 'PASTE_GENERATED_PASSWORD';
CREATE DATABASE lifeos OWNER lifeos;
\q
```

The `could not change directory` warning is harmless if the prompt appears. Run `CREATE` only once. If the role/database already exist, don't recreate them. Change a password with `ALTER ROLE lifeos WITH PASSWORD 'NEW_PASSWORD';` and update `.env.production`. For an external/managed PostgreSQL service, follow its network instructions and skip section 10.

## 7. Clone repo and select deploy branch

Example for a public repository:

```bash
mkdir -p /opt/lifeos
git clone --branch main --single-branch https://github.com/OWNER/REPOSITORY.git /opt/lifeos
cd /opt/lifeos
git status --short
```

Replace owner/repository/branch. For a private repository, use SSH and a read-only deploy key; don't put an access token in a URL or shell history. If the repo is already cloned, enter its directory instead.

```bash
cd /opt/lifeos
git fetch origin --prune
git switch main
git pull --ff-only origin main
```

Replace `main` with the intended production branch. For a new branch, use `git switch --track origin/BRANCH_NAME`. Inspect unexpected local source changes before switching or pulling.

## 8. Create `.env.production`

From the repo root:

```bash
cp .env.production.example .env.production
nano .env.production
```

Fill real values; retain the other keys in the example:

```dotenv
ENVIRONMENT=production
DATABASE_URL=postgresql://lifeos:YOUR_HEX_PASSWORD@host.docker.internal:5432/lifeos
SECRET_KEY=GENERATE_A_LONG_RANDOM_SECRET
FRONTEND_URL=https://lifeos.example.in
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=your-single-page-app-client-id
AUTH0_AUDIENCE=https://lifeos-api
MAIL_HOST=smtp.example.com
MAIL_PORT=587
MAIL_FROM=noreply@example.in
MAIL_STARTTLS=true
MAIL_USERNAME=your-smtp-username
MAIL_PASSWORD=your-smtp-password
VITE_API_BASE_URL=/api/v1
```

Generate `SECRET_KEY` with `openssl rand -hex 32`. `FRONTEND_URL` must be the final HTTPS origin with no path. `AUTH0_DOMAIN` has no scheme/trailing slash. Client ID is from the Auth0 SPA; audience is the Auth0 API Identifier. LifeOS production requires `MAIL_HOST`; Mailpit is for local development. URL-encode special DB password characters, or use the generated hex password. Optional VAPID values must be all set or all omitted.

Save nano with Ctrl+O, Enter, Ctrl+X. Restrict the secrets file:

```bash
chmod 600 .env.production
```

Never copy a developer's local `.env` to the server or commit production secrets.

## 9. Build images and create the Compose network

Run from the repository root:

    docker compose --env-file .env.production -f docker-compose.prod.yml config -q
    docker compose --env-file .env.production -f docker-compose.prod.yml build
    docker compose --env-file .env.production -f docker-compose.prod.yml create
    docker network ls --format '{{.Name}}'

The config command validates required variables and syntax. The create command prepares containers and network but does not start the app. Find this project's network ending in _default, then inspect its subnet:

    docker network inspect lifeos_default --format '{{(index .IPAM.Config 0).Subnet}}'

Use the actual network name and subnet shown. It can differ on another VPS.

## 10. Connect the API container to host PostgreSQL

Only for PostgreSQL installed on this same VPS. Get the config paths:

    sudo -u postgres psql -tAc "SHOW config_file"
    sudo -u postgres psql -tAc "SHOW hba_file"

Edit the returned config file (PostgreSQL 14 on Ubuntu 22.04 commonly uses /etc/postgresql/14/main/postgresql.conf):

    nano /etc/postgresql/14/main/postgresql.conf

Set the parameter exactly:

    listen_addresses = '*'

It is spelled listen_addresses, not listen. Edit the returned hba_file (often /etc/postgresql/14/main/pg_hba.conf) and add a rule using the subnet from section 9:

    host    lifeos    lifeos    YOUR_COMPOSE_SUBNET    scram-sha-256

Use 172.18.0.0/16 only if that is what this server printed. Put the rule before any matching reject rule. Keep port 5432 closed in UFW and the provider firewall. Restart PostgreSQL:

    systemctl restart postgresql
    systemctl status postgresql --no-pager

## 11. Point the domain/subdomain to the VPS

In the DNS manager authoritative for your domain, add an A record:

| Field | Value |
|---|---|
| Type | A |
| Name/Host | subdomain only, e.g. lifeos |
| Points to | VPS public IPv4 |
| TTL | Provider default |

For Hostinger nameservers, use hPanel → Domains → DNS / DNS Zone Editor. If the domain uses other nameservers, edit DNS there. Leave existing @ and www records untouched if they serve another site. Add an AAAA record only if IPv6, Nginx, and firewall are configured.

Check public DNS (install dnsutils if needed):

    apt-get install -y dnsutils
    dig @1.1.1.1 +short A lifeos.example.in
    dig @1.1.1.1 +short AAAA lifeos.example.in

The A query should return your VPS public IP. If blank/wrong, correct DNS and wait before requesting a certificate. References: [Hostinger DNS editor](https://www.hostinger.com/support/how-to-use-hostingers-dns-zone-editor/) and [Hostinger A records](https://www.hostinger.com/support/4468886-how-to-manage-a-records-at-hostinger/).

## 12. Configure host Nginx

LifeOS's host template proxies to 127.0.0.1:8080. Copy and edit it:

    cp nginx/lifeos.conf /etc/nginx/sites-available/lifeos
    nano /etc/nginx/sites-available/lifeos

Change server_name lifeos.example.com; to your real hostname, e.g. server_name lifeos.example.in;. Enable and validate:

    ln -s /etc/nginx/sites-available/lifeos /etc/nginx/sites-enabled/lifeos
    nginx -t
    systemctl reload nginx

If the link already exists, inspect it with ls -l /etc/nginx/sites-enabled/lifeos instead of creating another. Keep other domains' Nginx server blocks intact.

## 13. Configure Auth0 production URLs

In Auth0 Dashboard:

1. Open Applications → Applications → LifeOS Single Page Application → Settings.
2. Under Application URIs, add the exact origin https://lifeos.example.in to Allowed Callback URLs, Allowed Logout URLs, and Allowed Web Origins.
3. Preserve localhost entries if needed for development, then save.
4. Open Applications → APIs → LifeOS API and confirm its Identifier equals AUTH0_AUDIENCE in .env.production.

Auth0 checks callback URLs exactly. This app uses the site origin as its redirect URL; don't add a /callback suffix. See [Auth0 callback URL guidance](https://support.auth0.com/center/s/article/Callback-URL-Mismatch-Error-Is-Not-in-the-List-of-Allowed-Callback-URLs).

## 14. Start the app and issue HTTPS

Start services; the API runs Alembic migrations before Uvicorn:

    docker compose --env-file .env.production -f docker-compose.prod.yml up -d
    docker compose --env-file .env.production -f docker-compose.prod.yml ps
    docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=100 api

Check local frontend/API routes:

    curl -i http://127.0.0.1:8080/
    curl -i http://127.0.0.1:8080/api/v1/health

Scheduler/background health can be degraded briefly until its first cycle. Database and Auth0 checks should be healthy when configured and reachable.

Only request a certificate after public DNS points to this VPS and firewalls allow 80/443. Install Certbot via Snap if missing:

    apt-get install -y snapd
    snap install --classic certbot
    test -e /usr/local/bin/certbot || ln -s /snap/bin/certbot /usr/local/bin/certbot
    certbot --version

Request the certificate:

    certbot --nginx -d lifeos.example.in

Enter an email, accept the terms, and choose HTTP-to-HTTPS redirection if prompted. Test renewal:

    certbot renew --dry-run

Reference: [Certbot Nginx instructions](https://certbot.eff.org/instructions?os=snap&ws=nginx).

## 15. Verify deployment

    docker compose --env-file .env.production -f docker-compose.prod.yml ps
    nginx -t
    curl -I https://lifeos.example.in
    curl -i https://lifeos.example.in/api/v1/health
    git branch --show-current
    git log -1 --oneline

Open the HTTPS URL, sign in through Auth0, and test an API-backed page. Confirm the browser shows a valid certificate.

## 16. Deploy a later code update

SSH to the VPS and enter the repo root:

    ssh root@YOUR_VPS_PUBLIC_IP
    cd /opt/lifeos
    git status --short
    git branch --show-current

Confirm there are no unexpected source changes. .env.production is ignored by Git and should remain on the server. Fetch, switch to the intended branch, and fast-forward:

    git fetch origin --prune
    git switch main
    git pull --ff-only origin main

Replace main with the intended branch. For a new branch, use git switch --track origin/BRANCH_NAME. Inspect local changes before switching/pulling; don't deploy an unreviewed branch by accident.

Before a release that may change the schema, back up the database:

    install -d -m 700 /var/backups/lifeos
    sudo -u postgres pg_dump -Fc lifeos > "/var/backups/lifeos/lifeos-$(date +%F-%H%M%S).dump"

Validate and deploy:

    docker compose --env-file .env.production -f docker-compose.prod.yml config -q
    docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
    docker compose --env-file .env.production -f docker-compose.prod.yml ps
    docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=100 api

Migrations run at API startup. Check health and the changed feature. If Auth0 build values or other frontend build args changed, rebuild/recreate:

    docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build --force-recreate

Don't use git reset --hard, git clean, or delete Docker volumes for routine troubleshooting; they can destroy changes/data. Before reverting code, check compatibility with migrations already applied. Database restore is separate and should use a verified backup.

## 17. Operations and troubleshooting

Run from the repository root:

    docker compose --env-file .env.production -f docker-compose.prod.yml ps
    docker compose --env-file .env.production -f docker-compose.prod.yml logs -f api
    docker compose --env-file .env.production -f docker-compose.prod.yml logs -f frontend
    nginx -t
    systemctl status nginx --no-pager
    dig @1.1.1.1 +short A lifeos.example.in
    curl -i http://127.0.0.1:8080/
    curl -i http://127.0.0.1:8080/api/v1/health
    curl -I https://lifeos.example.in

| Symptom | First checks |
|---|---|
| DNS returns no A address | DNS record, authoritative nameservers, propagation. |
| DNS returns wrong IP | Correct only the app subdomain A record. |
| Browser reports DNS/NXDOMAIN | Check full hostname and public DNS lookup. |
| Browser times out but DNS is right | Provider firewall, UFW, public IP, Nginx 80/443 listeners. |
| Local port 8080 fails | Frontend container, build, or Compose binding. |
| Frontend loads but API health fails | Frontend proxy, API logs, DB access, migrations. |
| Certbot reports DNS error | Wait for public A record; check stale AAAA. |
| Auth0 callback mismatch | Add exact HTTPS origin in Auth0 and save. |
| API refuses production startup | Check secret, DB URL, frontend URL, Auth0, required MAIL_HOST. |

ipconfig /flushdns is a Windows command for your local computer, not Ubuntu over SSH. Use dig or getent hosts on the VPS.

## 18. Reuse this pattern for another app

Inspect a new app instead of copying LifeOS values blindly. Identify its Docker build context, runtime vs. build-time variables, database/migrations, persistent files, internal service ports, health endpoint, and secrets.

On a shared VPS, give each app its own repository directory, Compose project, environment file, database role/database, and Nginx site. Give each frontend a unique loopback-only port (e.g. 8081 for another app), add a DNS A record and certificate per hostname, and route by Nginx server_name. Keep container/database ports private. Back up before schema changes.

## Quick update checklist

For an already configured LifeOS VPS:

The current VPS path from this conversation is `/root/lifeos/LifeOS`. Use that path for this server. `/opt/lifeos` below is the example path for a new installation.

    cd /opt/lifeos
    git status --short
    git fetch origin --prune
    git switch main
    git pull --ff-only origin main
    docker compose --env-file .env.production -f docker-compose.prod.yml config -q
    docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
    docker compose --env-file .env.production -f docker-compose.prod.yml ps
    docker compose --env-file .env.production -f docker-compose.prod.yml logs --tail=100 api

Replace main as needed, then check https://lifeos.example.in and /api/v1/health.
