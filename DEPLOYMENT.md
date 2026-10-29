# Deploy Tastewell on AWS: beginner guide

Updated 2026-10-29. This guide is for the current **private pilot**. It puts the Next.js site, FastAPI API, Qloo harness, SQLite database, and Caddy web server on one Ubuntu machine. Follow the steps in order. Commands marked **Windows PowerShell** run on your computer; commands marked **Ubuntu terminal** run on the AWS server.

The Mumbai Lightsail instance is provisioned, but the app deployment is still in progress. The local Docker daemon is unavailable; a prior local live browser journey passed with real Qloo and a model. You will know the AWS deployment is ready only after the checks in Step 8 pass on the new server.

## What you are creating

- **Lightsail instance:** one rented Linux computer. It runs the app continuously.
- **Static IP:** a stable public address for that computer.
- **Domain/subdomain:** a readable name, such as pilot.example.com, pointed at the static IP.
- **Docker Compose:** starts the app's three containers and keeps their data volume.
- **Caddy:** handles HTTPS and asks for one username/password before showing any page or API result.
- **SQLite volume:** stores saved decisions on that instance. You must back it up.

This is a **single-password pilot**. Each browser has a signed session, and saved decisions are visible only to the browser that created them. The password is still shared; it is a demo gate, not an individual account. Clearing cookies loses access to that browser's decisions. Do not enter personal customer data. The Qloo key in this repository is configured for the hackathon host; verify its continued validity and usage terms before relying on the service beyond the pilot.

## Why Lightsail, and what it may cost

| Choice | Published starting price | Tradeoff |
| --- | ---: | --- |
| **Lightsail Linux 2 GB, 2 vCPU, 60 GB SSD** | **$12/month** | Chosen for the hackathon demo. Build images sequentially and measure runtime memory. |
| Lightsail Linux 4 GB, 2 vCPU, 80 GB SSD | $24/month | Upgrade path if the 2 GB build fails or sustained runtime memory pressure appears. |
| EC2 t3.small, 2 GB | $0.0209/hour in US East before disk and public IPv4 | More control, but more billing items and setup. No benefit for this first single-server pilot. |
| ECS/Fargate, App Runner, managed database | Multiple usage-based charges | Useful later for a larger service; extra setup and persistence work now. |

The Lightsail bundle figures come from [AWS Lightsail pricing](https://aws.amazon.com/lightsail/pricing/); the EC2 comparison uses [AWS T3 pricing](https://aws.amazon.com/ec2/instance-types/t3/). The selected Mumbai 2 GB plan shows **1.5 TB transfer** in the console. Mumbai and several other regions get half the headline allowance, according to [AWS transfer rules](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-faq-data-transfer-allowance.html). The 2 GB runtime capacity is still unmeasured; upgrade by creating a larger instance from a snapshot if needed.

Check **Billing and Cost Management → Credits** for the current balance, eligibility and expiration. The $12/month instance is billed hourly up to the monthly cap. Domain registration, snapshots, taxes, overage and any other AWS resources may be extra. [AWS credit terms](https://aws.amazon.com/awscredits/) exclude Route 53 domain registration.

An AWS **Free Plan** can end when its time or credits run out; [AWS's Free Tier FAQ](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-FAQ.html) says the account then closes and access to resources/data is lost unless you upgrade. **Set a reminder at least 14 days before the date shown in your console** to export the database and choose whether to upgrade. A stopped Lightsail instance still accrues instance charges; deletion stops that charge ([Lightsail billing FAQ](https://docs.aws.amazon.com/en_en/lightsail/latest/userguide/amazon-lightsail-frequently-asked-questions-faq-billing-and-account-management.html)).

## Before you start

Have these ready:

1. Your AWS sign-in with multifactor authentication. Avoid daily use of the root account; [AWS account security guidance](https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-best-practices.html) explains why.
2. A domain you control, or choose the temporary no-domain route near the end of this guide. A purchased domain is usually a separate charge.
3. Your Qloo API key and one model-provider key. Keep them on the server only. Do **not** paste them into chat, commit them to Git, or include them in the deployment archive.
4. Windows PowerShell with the built-in tar, ssh, and scp commands if you use the archive fallback in Step 5. Check them with Get-Command tar,ssh,scp. If ssh/scp are missing, install **OpenSSH Client** in Windows Settings → Optional features; [Microsoft's instructions](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse?pivots=windows-11&tabs=gui) show the steps.

### Step 1 — Set a cost alert and inspect your credits

In the [AWS console](https://console.aws.amazon.com/), open **Billing and Cost Management** from the account menu.

1. Open **Credits** (or the **Explore AWS** widget on Console Home). Record the remaining amount, exact expiration date, and eligible services. Confirm that Lightsail use is covered before provisioning.
2. Open **Budgets → Create budget**. Choose **Monthly cost budget** (the simplified template is fine). Set a **$25 monthly budget** and your email address. If the console offers forecast alerts, set one around **$40**. This is a warning, not a spending cap. Review the AWS Free Tier and Credits pages weekly. AWS's [beginner cost tutorial](https://docs.aws.amazon.com/hands-on/latest/control-your-costs-free-tier-budgets/control-your-costs-free-tier-budgets.html) shows the current console flow.
3. Keep a note of the Free Plan deadline. Decide before it arrives whether you will upgrade to Paid or remove the resources after backing up.

### Step 2 — Create the Lightsail server

Open [Lightsail](https://lightsail.aws.amazon.com/). AWS's [instance walkthrough](https://docs.aws.amazon.com/lightsail/latest/userguide/getting-started-with-amazon-lightsail.html) shows the same console screens.

1. On the Lightsail home page, choose **Create instance**.
2. Select the region nearest your pilot users. If users are primarily in India, **Asia Pacific (Mumbai)** is a reasonable first choice. Otherwise choose their nearest available region. Keep the same region for the static IP. Availability zone can stay at the default.
3. Choose **Linux/Unix → OS Only → Ubuntu 24.04 LTS**. Do not choose a WordPress, LAMP, or preconfigured Docker image; this repository installs its own stack. Choose a **dual-stack/public IPv4** bundle so a normal A record works.
4. Select the **2 GB / 2 vCPU / 60 GB** plan at $12/month for the small demo. Read the price and transfer allowance on the confirmation screen.
5. Use the region's **default SSH key** unless you already manage your own key. Name the instance something recognizable, such as tastewell-pilot. Choose **Create instance**.

You can connect immediately using **instance → Connect → Connect using SSH** in the Lightsail browser. That browser terminal is the easiest place to run the Ubuntu commands below.

### Step 3 — Give it a stable IP and set the firewall

In Lightsail, choose **Networking → Create static IP**, select the **same region and instance**, name it, and create it. Copy the displayed IPv4 address. Without a static IP, a stop/start can change the address and break DNS ([AWS static IP guide](https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-create-static-ip.html)).

Open the instance's **Networking** tab and inspect **IPv4 firewall** rules:

- **HTTP, TCP 80:** allow all. Caddy uses this to issue/renew HTTPS certificates and redirect visitors.
- **HTTPS, TCP 443:** allow all. This is the public app entrance.
- **SSH, TCP 22:** restrict to your current public IP where practical. Keep the Lightsail browser SSH option enabled if you use it.
- **Do not open 3000 or 8000.** Those are internal container ports.

Lightsail has separate IPv4 and IPv6 firewalls. This guide creates **only an A record** (IPv4). If you later publish an AAAA record, configure and test IPv6 separately. See [AWS's firewall rule reference](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-firewall-rules-reference.html).

### Step 4 — Point a domain at the server

At the company where you manage DNS for example.com, add one **A record**:

| Field | Example |
| --- | --- |
| Name/host | pilot |
| Type | A |
| Value | The static IPv4 from Step 3 |
| TTL | 300 seconds, or the provider default |

The result is pilot.example.com. Replace that name everywhere below with yours. You can instead create a [Lightsail DNS zone](https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-create-dns-entry.html), but using your existing DNS provider avoids changing the whole domain's nameservers. From your Windows PowerShell, run nslookup pilot.example.com and wait until it shows the static IP. DNS changes can take time to propagate.

Caddy needs the domain to resolve to this host and ports **80/443** reachable to issue HTTPS automatically ([Caddy HTTPS docs](https://caddyserver.com/docs/automatic-https)). Do not share the URL until HTTPS and password protection both work.

### Step 5 — Get the published release

The tested source is published at [Spark960/TasteWell](https://github.com/Spark960/TasteWell). On Ubuntu, clone it with `git clone https://github.com/Spark960/TasteWell.git /home/ubuntu/tastewell` and check the release SHA with `git -C /home/ubuntu/tastewell log -1 --oneline`. The archive method below is only for deploying later local changes that have not been pushed.

In **Windows PowerShell**, change to this repository's root and run:

~~~powershell
cd "L:\vs code projects\_hackathons\devpost\qloo"
tar --exclude='*/__pycache__' --exclude='*.pyc' -czf tastewell-deploy.tgz .dockerignore .env.example deploy backend/app backend/pyproject.toml frontend/app frontend/lib frontend/public frontend/package.json frontend/package-lock.json frontend/next.config.ts frontend/tsconfig.json frontend/next-env.d.ts
tar -tzf tastewell-deploy.tgz | Select-Object -First 30
~~~

Check the list. It must **not** contain .env, frontend/.env.local, backend/data, .aws, .codex, or a private key. This archive is a deployment package, not a backup of the full repository.

To use scp, download the Lightsail default private key from **Lightsail → Account → SSH keys → Default keys → download icon** for the chosen region ([AWS key guide](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-managing-ssh-keys.html)). Store the .pem file securely and never upload it. Replace the sample key path and sample IP below with your own. Ubuntu's default login name is **ubuntu**.

~~~powershell
scp -i "$env:USERPROFILE\Downloads\LightsailDefaultKey-ap-south-1.pem" .\tastewell-deploy.tgz ubuntu@203.0.113.10:/home/ubuntu/
~~~

If scp reports a key-permission error, follow [AWS's SSH key instructions](https://docs.aws.amazon.com/en_en/lightsail/latest/userguide/amazon-lightsail-ssh-using-terminal.html) for your computer; do not disable key checks. In the **Ubuntu terminal**, unpack and inspect:

~~~bash
mkdir -p /home/ubuntu/tastewell
tar -xzf /home/ubuntu/tastewell-deploy.tgz -C /home/ubuntu/tastewell
cd /home/ubuntu/tastewell
ls deploy/compose.yaml frontend/package-lock.json backend/pyproject.toml
~~~

For later code updates, create and transfer a new archive from the reviewed working tree, back up the database, unpack over the same directory, and rebuild the containers. A private Git repository is more convenient for frequent releases, but it requires carefully reviewing which local files you commit.

### Step 6 — Install Docker on Ubuntu

Run these in the **Lightsail Ubuntu terminal**. They follow [Docker's official Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/). Docker groups all app parts together, so you do not have to install Node, Python, Qloo, or Caddy separately on Ubuntu.

~~~bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
sudo docker run --rm hello-world
~~~

The repository uses Ubuntu 24.04's codename **noble** above. If you selected a different Ubuntu version, use Docker's linked instructions rather than that literal sources block. We use **sudo docker** throughout; adding your account to the docker group is unnecessary for this guide because Docker access effectively grants root-level control.

### Step 7 — Put secrets and site settings on the server

In **Ubuntu**, create the app's private credential file:

~~~bash
cd /home/ubuntu/tastewell
cp .env.example .env
nano .env
chmod 600 .env
~~~

In nano, set **QLOO_API_KEY**, **LLM_PROVIDER**, the matching provider key (for example GEMINI_API_KEY if LLM_PROVIDER=gemini), and **SESSION_SECRET**. Generate a random session secret with `openssl rand -hex 32` on Ubuntu and paste the output only into `.env`; keep it stable across redeploys or existing browser sessions will lose access. Keep QLOO_BASE_URL and QLOO_TRUSTED_BASE_URL pointing at the hackathon host only while your hackathon key is valid. Save with **Ctrl+O, Enter, Ctrl+X**. Other blank provider keys can remain blank. Never put real keys in .env.example.

Choose a long unique password for the pilot. Generate a **hash** in Ubuntu:

~~~bash
sudo docker run --rm -it caddy:2.10 caddy hash-password
~~~

Enter the password when prompted, then copy the resulting hash. Create a separate settings file **outside the repository**:

~~~bash
nano /home/ubuntu/tastewell-runtime.env
chmod 600 /home/ubuntu/tastewell-runtime.env
~~~

Put these lines in it, replacing the domain and hash. Keep the **single quotes around the hash** so dollar signs are not expanded:

~~~text
SITE_ADDRESS=pilot.example.com
HTTP_BIND=0.0.0.0
HTTPS_BIND=0.0.0.0
HTTP_PORT=80
HTTPS_PORT=443
ACCESS_USER=pilot
ACCESS_PASSWORD_HASH='$2a$...your complete generated hash...'
~~~

The username and hashed password are read by Compose; the **plaintext password is not stored here**. Anyone with Docker/admin access to the server can still inspect container environment variables, so limit server access. The app .env is loaded directly into the backend container.

### Step 8 — Build, start, and verify

Stay in **/home/ubuntu/tastewell**. First check that Compose can read all required settings:

~~~bash
sudo docker compose --env-file /home/ubuntu/tastewell-runtime.env -f deploy/compose.yaml config --quiet
sudo docker compose --env-file /home/ubuntu/tastewell-runtime.env -f deploy/compose.yaml build backend
sudo docker compose --env-file /home/ubuntu/tastewell-runtime.env -f deploy/compose.yaml build frontend
~~~

The first builds download images and dependencies and can take several minutes. On the 2 GB plan, build one service at a time. The instance has a 2 GB swap file for build headroom; inspect `free -h`, `df -h /`, and `sudo docker stats --no-stream` before deciding whether to upgrade. The backend runs as Linux user ID 10001. Initialize write permission for its persistent database volume before first start:

~~~bash
sudo docker compose --env-file /home/ubuntu/tastewell-runtime.env -f deploy/compose.yaml run --rm --no-deps --user root backend chown 10001:10001 /app/backend/data
sudo docker compose --env-file /home/ubuntu/tastewell-runtime.env -f deploy/compose.yaml up -d
sudo docker compose --env-file /home/ubuntu/tastewell-runtime.env -f deploy/compose.yaml ps
sudo docker compose --env-file /home/ubuntu/tastewell-runtime.env -f deploy/compose.yaml logs --tail=100 caddy backend
~~~

All three services should show **running**. Caddy may need a minute after DNS propagation to obtain a certificate. In a private browser window, open **https://pilot.example.com/decision**. Confirm you see a password prompt, your chosen credentials work, and the page loads without a browser certificate warning.

Then open **https://pilot.example.com/api/health** in the same browser; it should return JSON with status **ok**. Open **https://pilot.example.com/api/qloo/status** and check **ready: true** before trying a real decision. Finally, create a small test decision in /decision, open it from Saved decisions, restart the backend, and confirm it still exists:

~~~bash
sudo docker compose --env-file /home/ubuntu/tastewell-runtime.env -f deploy/compose.yaml restart backend
~~~

Cloud Qloo readiness and a real agent review are required gates. A healthy /api/health response alone does not prove Qloo works. The optional deploy/smoke_test.sh script can run from Git Bash/WSL with TASTEWELL_URL, ACCESS_USER, and ACCESS_PASSWORD set locally; avoid putting the plaintext password in a committed file or a shared shell history.

### Step 9 — Back up, monitor, update, and stop

The database lives in Docker's **tastewell_decision_data** volume on this instance. At least weekly, and before each update, make a backup **outside that volume**. The simplest consistent copy pauses the backend briefly. Run in Ubuntu:

~~~bash
mkdir -p /home/ubuntu/tastewell-backups
cd /home/ubuntu/tastewell
sudo docker compose --env-file /home/ubuntu/tastewell-runtime.env -f deploy/compose.yaml stop backend
sudo docker run --rm -v tastewell_decision_data:/source:ro -v /home/ubuntu/tastewell-backups:/backup alpine:3.20 sh -c 'test -f /source/decisions.sqlite && cp /source/decisions.sqlite /backup/decisions.sqlite'
sudo chown ubuntu:ubuntu /home/ubuntu/tastewell-backups/decisions.sqlite
chmod 600 /home/ubuntu/tastewell-backups/decisions.sqlite
sudo docker compose --env-file /home/ubuntu/tastewell-runtime.env -f deploy/compose.yaml start backend
ls -lh /home/ubuntu/tastewell-backups/decisions.sqlite
~~~

If the copy fails, **start backend anyway**, then diagnose the file/volume before trusting the backup. Download a copy to a secure folder on your Windows computer with scp (reverse the source and destination in Step 5). A backup kept only on the same Lightsail instance is lost if the instance is deleted. Optionally enable [Lightsail automatic snapshots](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-configuring-automatic-snapshots.html); AWS lists snapshot storage at **$0.05/GB-month** on its [pricing page](https://aws.amazon.com/lightsail/pricing/). Verify a restore on a disposable volume or host before depending on either method.

Check **Billing → Budgets, Credits, and Free Tier** weekly, along with Lightsail CPU/disk/network graphs. In Ubuntu, use sudo docker compose ... ps and logs to inspect service health. For an update, make a backup, upload a fresh reviewed archive, unpack it, run the Step 8 build and up -d commands, and repeat the browser checks.

To stop **only the app containers**, run sudo docker compose ... down. This leaves the database volume but **the Lightsail instance still costs money**. Never add **-v** to down unless you intentionally want to remove the database volume. To end AWS charges, download/verify the backup, then delete the Lightsail **instance**, any **snapshots** you do not need, and the **static IP** if it remains detached. Remove the DNS record. Domain registration can continue to renew separately. Do this before the Free Plan deadline if you will not upgrade.

## If you do not have a domain yet

You can test privately through an **SSH tunnel** without public HTTPS. In /home/ubuntu/tastewell-runtime.env, set SITE_ADDRESS=:80, HTTP_BIND=127.0.0.1, HTTP_PORT=8080, HTTPS_BIND=127.0.0.1, and HTTPS_PORT=8443. Start the stack using Step 8. Remove the public HTTP/HTTPS firewall rules from Step 3 for this temporary mode. On Windows, run:

~~~powershell
ssh -i "$env:USERPROFILE\Downloads\LightsailDefaultKey-ap-south-1.pem" -L 8080:127.0.0.1:8080 ubuntu@203.0.113.10
~~~

Keep that terminal open and visit **http://localhost:8080/decision** on that Windows computer. The traffic between your computer and the server goes through SSH, and the app still asks for its password. This is for your own test, not a shareable pilot URL. Switch to the domain/HTTPS settings before inviting other testers.

## Common problems

| Symptom | Check |
| --- | --- |
| Browser cannot connect | Instance running; static IP; A record from nslookup; Lightsail IPv4 firewall 80/443; Compose ps. |
| Browser reports certificate error | DNS still points elsewhere, 80/443 blocked, or Caddy is still obtaining a certificate. Inspect Caddy logs. Do not ignore the warning. |
| No password prompt | You may be visiting the wrong host or an old cached page. Check Caddy logs and an incognito window before sharing the URL. |
| Site loads but /api/health fails | Inspect backend logs; check that backend container is running. |
| Qloo status says harness spawn timeout | Inspect backend logs, QLOO_API_KEY and both Qloo host settings in .env, and credential validity. Run sudo docker compose ... exec backend qloo --version to check the harness installation. Do not treat a healthy homepage as a working Qloo integration. |
| Backend cannot write decisions.sqlite | Rerun the Step 8 permission initialization as root, then restart backend. |
| Build fails or host becomes unresponsive | Inspect free disk and RAM with df -h and free -h; the 2 GB plan is especially likely to struggle. |
| Unexpected AWS spending | Inspect Billing by service/region, Lightsail instances, snapshots, detached static IPs, domain charges, and transfer. A stopped instance is still billed. |

The stack is suitable for a **small private pilot** after its build and smoke tests pass. It does not provide recoverable user accounts, automated off-site backups, a retention policy, or measured production capacity. Those require further engineering before a public service.
