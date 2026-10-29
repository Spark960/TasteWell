# Update the hosted judge frontend

The hosted site does not update when code is pushed to GitHub. Run this short
rollout on the existing Lightsail instance after the frontend change is merged
into `main`. It rebuilds and restarts only the frontend container; the backend,
database volume, Caddy configuration, and private environment files stay in
place.

## On the Lightsail Ubuntu terminal

1. Open **Lightsail → tastewell-demo → Connect using SSH**. Run:

   ```bash
   cd /home/ubuntu/tastewell
   git status --short
   git rev-parse --short HEAD
   ```

   If `git status --short` lists local edits, stop and inspect them before
   pulling. Keep `/home/ubuntu/tastewell/.env` and
   `/home/ubuntu/tastewell-runtime.env` private; do not print or replace them.

2. Pull the published frontend and rebuild that image:

   ```bash
   git pull --ff-only origin main
   sudo docker compose --env-file /home/ubuntu/tastewell-runtime.env -f deploy/compose.yaml build frontend
   sudo docker compose --env-file /home/ubuntu/tastewell-runtime.env -f deploy/compose.yaml up -d --no-deps frontend
   sudo docker compose --env-file /home/ubuntu/tastewell-runtime.env -f deploy/compose.yaml ps
   ```

   Confirm that `frontend`, `backend`, and `caddy` are running. The first
   build may take a few minutes on the 2 GB host.

## Check the public page

1. Open `https://tastewell.35-154-50-144.sslip.io/decision` in a private
   browser window and sign in with the existing judge credentials from
   Devpost's judge-only field. A request without credentials should receive
   an HTTP `401` challenge.
2. Confirm the left guide reads **Venue brief → Qloo shortlist → Agent review
   → Your pilot → Result**. The first screen should explain that Qloo finds and
   ranks artists, the agent reviews the evidence, and the operator decides.
3. Open the illustrative example. Its notice must say the data is invented
   and that a new decision is needed for live Qloo and agent review. Then
   return to the brief. If you run a live test, check that **Review the pilot
   choice** still completes and cites saved Qloo evidence.

If the new copy does not appear, check the frontend logs without printing
environment variables:

```bash
cd /home/ubuntu/tastewell
sudo docker compose --env-file /home/ubuntu/tastewell-runtime.env -f deploy/compose.yaml logs --tail=80 frontend
```

The full deployment and backup guide remains in [DEPLOYMENT.md](DEPLOYMENT.md).
