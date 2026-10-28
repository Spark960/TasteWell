# Private preview deployment

This Compose stack runs the Next.js frontend, FastAPI backend, Qloo MCP
harness, and Caddy on one machine. Caddy protects every route with one
operator password. It is a private preview, not multi-user authentication:
anyone with the password can see all saved decisions. Use a dedicated host
and do not distribute credentials beyond the preview group.

The backend image installs the official `@qloo/qloo-harness` at version
`0.1.26` with Node 22. The SQLite database lives in the `decision_data`
volume. The frontend calls `/api` on the same origin. No provider secret is
built into either image.

## AWS target

For a first private preview, use one Ubuntu **Lightsail 4 GB** instance with
a static IP. AWS currently lists this Linux plan at **$24/month** with an
80 GB SSD and a transfer allowance; region-specific transfer allowances and
overage charges still apply. The 2 GB plan is $12/month, but building both
images on the instance may leave too little memory. An EC2 `t3.small` has
2 GiB RAM at $0.0209/hour in us-east-1 before storage and other charges;
the old `t3.micro` deployment note is too small for this three-container
build. These are deployment sizing assumptions until a real build and load
test runs. See [Lightsail pricing](https://aws.amazon.com/lightsail/pricing/),
[EC2 T3 pricing](https://aws.amazon.com/ec2/instance-types/t3/), and
[Lightsail transfer rules](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-faq-data-transfer-allowance.html).

Create the instance and static IP in the desired AWS region, point a domain
at that IP, allow inbound 80/443, and limit SSH to the operator's IP. Install
Docker with Compose, copy the repository and private `.env` to the host, and
follow the steps below. Keep the SQLite volume on persistent instance storage
and take a backup before upgrades. This private-preview stack has no
multi-user ownership or automated backup policy yet.

1. Copy the root `.env.example` to `.env` and fill the Qloo and chosen model
   provider credentials. Keep `.env` on the host and out of Git.
2. Choose a password and hash it with `docker run --rm caddy:2.10 caddy
   hash-password`. Set `ACCESS_USER` and `ACCESS_PASSWORD_HASH` in your shell.
   Keep the plaintext password separately for the smoke test.
3. For a local private preview, leave `SITE_ADDRESS` unset and run
   `docker compose -f deploy/compose.yaml up --build -d`. Open
   `http://localhost:8080/decision`. Local HTTP is for same-machine testing.
4. For a remote host, point a domain at the host, set `SITE_ADDRESS` to that
   domain, set `HTTP_BIND=0.0.0.0`, `HTTPS_BIND=0.0.0.0`, `HTTP_PORT=80`,
   and `HTTPS_PORT=443`. Open both ports so
   Caddy can obtain HTTPS automatically. Then run the same Compose command.
   Do not expose the private preview over plain HTTP.
5. Set `TASTEWELL_URL`, `ACCESS_USER`, and plaintext `ACCESS_PASSWORD` in a
   shell and run `bash deploy/smoke_test.sh` from another machine.

The stack has not been built on this workstation because its Docker daemon
is unavailable. Before a remote rollout, build it on a Docker host, run the
smoke test, verify Qloo readiness, and check a restart preserves decisions.

The [Qloo hackathon kit](https://github.com/qloo/qloo-hackathon-kit) documents
the harness installation and Node requirement. Caddy's
[basic authentication](https://caddyserver.com/docs/caddyfile/directives/basic_auth)
uses a hashed password; its reverse proxy keeps `/api` on the same origin.
