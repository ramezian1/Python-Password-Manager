# Python Password Manager

> **Live Demo:** Deploy your own instance in minutes — see [Deploy to Render](#deploy-to-render) below.

A secure password manager with both a **CLI** and a **Flask web interface**. Passwords are encrypted with **Fernet** (AES-128-CBC + HMAC) via the `cryptography` library. The encryption key is **derived from your master password with scrypt** and is never written to disk.

---

## ⚠️ Security notice for anyone who used a version before v2

Earlier versions stored the Fernet key in a `secret.key` file **and that file was committed to this repository's git history**, alongside `passwords.txt`. Anyone who cloned the repo could decrypt the entire vault.

If you ran an earlier version:

1. **Rotate every password stored in the vault** at the real service. Treat them as public.
2. Pull this version. Your vault is migrated automatically on next login (see [Upgrading](#upgrading-from-v1)).
3. Delete the `*.migrated` leftovers once you have confirmed the new vault works — they still contain the old key.
4. If you published your own fork, purge the files from history and force-push:
   ```bash
   git rm --cached secret.key passwords.txt   # already done in this version
   pip install git-filter-repo
   git filter-repo --invert-paths --path secret.key --path passwords.txt
   git push --force
   ```
   History rewriting is a courtesy, not a fix. Git hosts cache unreachable objects, so **step 1 is the only step that actually protects you.**

---

## Features

- **Master-password-derived encryption** — scrypt (n=2¹⁴, r=8, p=1) stretches your master password into the Fernet key; nothing secret is stored on disk
- **Add** passwords with a service/website, username, and password
- **Generate** cryptographically secure passwords (customizable length)
- **Find & copy** — retrieves a password and copies it to clipboard (web: one click, CLI: `pyperclip`)
- **List all entries** — shows every saved service and username (no passwords displayed)
- **Update** an existing password (generate or manual)
- **Delete** an entry with confirmation
- **Change master password** — re-encrypts the whole vault under a fresh salt
- **Multiple accounts per service** — entries are keyed by *(service, username)*, so two Gmail accounts coexist
- **Password strength checker** — enforces lowercase, uppercase, digit, and symbol
- **Atomic writes** — the vault is written via temp-file + rename, so a crash mid-save cannot truncate it
- **Idle lock** — the web UI drops the key from memory after 15 minutes of inactivity

## Interfaces

| Mode | How to run | Best for |
|---|---|---|
| Web (Flask) | `FLASK_DEV=1 python app.py` | Browser-based UI, shareable demo |
| CLI | `python main.py` | Terminal use, offline |

## Security Model

| Item | How it's handled |
|---|---|
| Master password | Never stored. scrypt-derived; only a 32-byte *verifier* half is saved in `vault.json` |
| Encryption key | Derived from the master password at unlock, held in memory only |
| Stored passwords | Fernet-encrypted inside `vault.json` (local only, git-ignored) |
| Password verification | `hmac.compare_digest` — constant-time, no timing leak |
| Web session | Signed cookie holds only an opaque session id; the key lives in server memory, keyed by that id |
| Cookie flags | `HttpOnly`, `SameSite=Lax`, and `Secure` outside dev mode |
| Password input (CLI) | `getpass` — hidden from terminal |
| Password copy (web) | JS `navigator.clipboard` — fetched on demand, never rendered into the HTML |
| Password copy (CLI) | `pyperclip` — copied to clipboard, not printed |

**There is no password recovery.** The key is derived from your master password; if you forget it, the vault is unreadable. That is the point.

### Known limitations

- **Service and username are stored in cleartext** in `vault.json` — only passwords are encrypted. Someone with the file learns *which* accounts you have, not their passwords.
- **No CSRF tokens.** `SameSite=Lax` blocks the cross-site POSTs that would matter here, but a token would be better.
- **Single-user, single-worker.** The unlocked key lives in one process's memory (see below).
- **No rate limiting** on login attempts.

## Requirements

- Python 3.10+ (uses `X | None` type syntax)
- Dependencies listed in `requirements.txt`

```
cryptography>=42.0.0
pyperclip>=1.8.2
flask>=3.0.0
gunicorn>=21.2.0
```

## Installation

```bash
git clone https://github.com/ramezian1/Python-Password-Manager.git
cd Python-Password-Manager
pip install -r requirements.txt
```

## Configuration

| Env var | Required | Purpose |
|---|---|---|
| `FLASK_SECRET_KEY` | **Yes**, in production | Signs session cookies. The app refuses to start without it — an unstable value logs everyone out on restart. Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_DEV` | No | Set to `1` for local development: uses a throwaway session key and allows plain HTTP cookies |
| `PORT` | No | Port for `python app.py` (default `5000`) |

## Usage

### Web Interface (Flask)

```bash
FLASK_DEV=1 python app.py
```

Open `http://localhost:5000` in your browser.

1. On first run you will be directed to `/setup` to create your master password.
2. Log in at `/login`.
3. Use the dashboard to add, copy, edit, or delete entries.

### CLI

```bash
python main.py
```

### Menu options

```
=== Password Manager ===
  1. Add password
  2. Find / copy password
  3. List all entries
  4. Update password
  5. Delete entry
  6. Change master password
  7. Exit
```

## Web Routes

| Route | Method | Description |
|---|---|---|
| `/` or `/login` | GET / POST | Master password login (migrates a v1 vault on first success) |
| `/setup` | GET / POST | First-run master password creation |
| `/logout` | GET | Drop the key from memory and clear the session |
| `/dashboard` | GET | View all saved entries |
| `/add` | GET / POST | Add a new entry |
| `/update?service=&username=` | GET / POST | Update an existing entry |
| `/delete` | POST (form) | Delete an entry — `service` + `username` fields |
| `/view` | POST (form) | Return decrypted password (AJAX) |
| `/generate` | POST (JSON) | Generate a secure password (AJAX) |

`/update` and `/delete` take the entry identity as parameters rather than path segments, because a service name may be empty or contain a `/`.

## Upgrading from v1

The first successful login (web or CLI) detects a v1 vault and converts it:

1. Verifies your existing master password against the old `master.hash`.
2. Decrypts every entry with the old `secret.key`.
3. Re-encrypts them under a key derived from the same master password, into `vault.json`.
4. Renames `secret.key`, `passwords.txt`, and `master.hash` to `*.migrated`.

Your master password does not change. **Delete the `*.migrated` files once you have confirmed the vault works** — they still contain the old on-disk key.

> Entries whose *service* or *username* contained a `:` were already corrupted by v1's `service:username:ciphertext` line format and cannot be recovered. The migration reports how many it had to skip rather than dropping them silently.

## Deploy to Render

This repo ships with a `render.yaml` and `Procfile` for zero-config deployment on [Render](https://render.com).

### Steps

1. Fork or push this repo to your GitHub account.
2. Go to [https://dashboard.render.com](https://dashboard.render.com) and click **New → Web Service**.
3. Connect your GitHub repo (`Python-Password-Manager`).
4. Render will auto-detect `render.yaml` and pre-fill all settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn --workers 1 --threads 4 app:app`
   - **Env var:** `FLASK_SECRET_KEY` auto-generated
   - **Disk:** 1 GB persistent volume mounted at `/opt/render/project/src` (keeps `vault.json` across deploys)
5. Click **Create Web Service**.
6. Once deployed, visit your Render URL (e.g. `https://python-password-manager.onrender.com`).
7. On first visit you will be prompted to create your master password.

> **Do not raise the worker count.** The unlocked vault key is held in one process's memory, so a second worker would not see your login and would appear to log you out at random. Scaling this safely needs a shared session store, which is on the roadmap.

### Railway (alternative)

1. Install the [Railway CLI](https://docs.railway.app/develop/cli): `npm install -g @railway/cli`
2. `railway login`
3. `railway init` and select this repo.
4. `railway up`
5. Set `FLASK_SECRET_KEY` in your Railway project environment variables.

> **Note:** The free tier on Render spins down after 15 minutes of inactivity. The first request after sleep may take ~30 seconds — and because the key is in memory, a spin-down logs you out.

## File Structure

```
Python-Password-Manager/
├── app.py               # Flask web application
├── main.py              # CLI application + shared core logic
├── requirements.txt     # Python dependencies
├── Procfile             # Gunicorn start command (Render/Railway)
├── render.yaml          # Render deployment configuration
├── .gitignore           # Excludes sensitive files
├── templates/
│   ├── base.html        # Shared layout (navbar, flash messages)
│   ├── login.html       # Master password login page
│   ├── setup.html       # First-run setup page
│   ├── dashboard.html   # Vault table with actions
│   ├── add.html         # Add entry form
│   └── update.html      # Update entry form
├── static/
│   └── style.css        # Dark theme styles
└── vault.json           # Salt, verifier, and encrypted entries (auto-generated, git-ignored)
```

## Roadmap

- Encrypt service/username too, not just passwords
- CSRF tokens on state-changing forms
- Shared session store so the app can run multiple workers
- Rate limiting on login
- Export / import encrypted vault backup
- Search entries by keyword
- 2FA / TOTP support
