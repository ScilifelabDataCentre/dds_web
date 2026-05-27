# Repository Overview

Forked from [ScilifelabDataCentre/dds_web](https://github.com/ScilifelabDataCentre/dds_web) upstream.
Rebranded and configured for **Epigenica** deployment at `dds.epigenica.se`.

## Branding status

| Location | Status |
|---|---|
| `compose.yml` — `DDS_VERSION`, labels | Epigenica |
| `sensitive/dds_app.cfg.example` — `SITE_NAME`, mail sender | Epigenica |
| `ansible/roles/dds/vars/main.yml.example` — `dds_site_name`, mail sender | Epigenica |
| `ansible/playbook.yml` — play name | Epigenica |
| `ansible/roles/dds/meta/main.yml` — role description | Epigenica |
| `README.md` line 3 — link to `ScilifelabDataCentre/dds_web` | Intentional upstream attribution — keep |
| `compose.yml` line 55 — `ghcr.io/scilifelabdatacentre/dds-backend` image | Upstream container registry — only change if you build/host your own image |

---

## File / folder reference

| Path | Purpose |
|---|---|
| `compose.yml` | Defines four services: `db` (MariaDB 10.11.5), `redis` (Redis 7), `backend` (DDS Flask/Gunicorn), `traefik` (v3.6.7 reverse proxy + Let's Encrypt TLS). Bridge network `dds_web_internal`; named volume for ACME certs. |
| `.env.example` | Template for `.env`. Sets `DDS_HOST`, `ACME_EMAIL`, database/Redis passwords, image version, and optional Traefik port overrides. Copy to `.env` before first run. |
| `.gitignore` | Excludes `.env`, `sensitive/dds_app.cfg`, `logs/`, `data/`, `.DS_Store`. Only `*.example` files are committed. |
| `sensitive/dds_app.cfg.example` | Template for the Flask app config (`dds_app.cfg`). Contains `SECRET_KEY`, DB URI, mail settings, Redis URL, and superadmin credentials. Copy to `sensitive/dds_app.cfg` and fill in real values. |
| `README.md` | Deployment guide: prerequisites, step-by-step deploy, scaling the backend, database init, pre-certificate testing, Traefik/ACME troubleshooting, and Ansible summary. |
| `ansible/` | Ansible assets for automated remote deployment. |
| `ansible/ansible.cfg` | Sets `inventory = inventory.yml`, `roles_path = roles`, disables retry files, enables sudo. Includes commented `vault_password_file` option. |
| `ansible/playbook.yml` | Single play targeting the `dds` host group; applies the `dds` role. |
| `ansible/inventory.example.yml` | Template for `inventory.yml` (gitignored). Defines host `dds-epigenica` with `ansible_host`, `ansible_user`, `ansible_port` placeholders. |
| `ansible/requirements.yml` | Declares `community.docker >= 3.4.0` collection dependency. Install once with `ansible-galaxy collection install -r requirements.yml`. |
| `ansible/.gitignore` | Excludes `.vault_pass`, `inventory.yml`, `.ansible/` from git. |
| `ansible/README.md` | Ansible-specific docs: prerequisites, vault workflow, optional role variables table, deploy and re-deploy commands. |
| `ansible/roles/dds/defaults/main.yml` | Non-secret role defaults: image version (`v2.14.3`), replica count (`1`), directory paths, MariaDB/Redis UIDs, `dds_app.cfg` tuning knobs, Traefik port overrides. |
| `ansible/roles/dds/vars/main.yml` | **Encrypted with Ansible Vault** — contains all secrets (passwords, secret key, mail credentials, superadmin, install path). Never committed in plaintext. |
| `ansible/roles/dds/vars/main.yml.example` | Plaintext template documenting every vault variable with placeholder values. Copy, fill, then encrypt. |
| `ansible/roles/dds/tasks/main.yml` | Role tasks: validates secrets, creates host directories with correct ownership (backend UID 1001, MariaDB UID 999), deploys `compose.yml`/`.env`/`dds_app.cfg`, flushes handlers, starts/scales the stack. |
| `ansible/roles/dds/handlers/main.yml` | Single handler `Restart DDS stack` — runs `docker compose up` with `recreate: always` when config files change. |
| `ansible/roles/dds/meta/main.yml` | Role metadata: name, description, MIT license, min Ansible 2.14, no dependencies. |
| `ansible/roles/dds/templates/env.j2` | Jinja2 template that renders `.env` from vault variables. Escapes `$` as `$$` for Docker Compose compatibility. |
| `ansible/roles/dds/templates/dds_app.cfg.j2` | Jinja2 template that renders `sensitive/dds_app.cfg`. URL-encodes DB/Redis passwords; conditionally includes mail credentials. |
