# Python Password Manager

> **Live Demo:** Deploy your own instance in minutes — see [Deploy to Render](#deploy-to-render) below.

A secure password manager with both a **CLI** and a **Flask web interface**. Passwords are encrypted with **Fernet** (AES-128) via the `cryptography` library. The master password is never stored in plain text — only its SHA-256 hash is saved locally.

## Features

- **Master password protection** — hashed with SHA-256, set on first run, never hardcoded
- **Add** passwords with a service/website, username, and password
- **Generate** cryptographically secure passwords (customizable length)
- **Find & copy** — retrieves a password and copies it to clipboard (web: one click, CLI: `pyperclip`)
- **List all entries** — shows every saved service and username (no passwords displayed)
- **Update** an existing password (generate or manual)
- **Delete** an entry with confirmation
- **Password strength checker** — enforces lowercase, uppercase, digit, and symbol
- **Fernet encryption** — all stored passwords are encrypted at rest
- **`.gitignore` protection** — `secret.key`, `passwords.txt`, and `master.hash` are excluded from version control

## Interfaces

| Mode | How to run | Best for |
|---|---|---|
| Web (Flask) | `python app.py` | Browser-based UI, shareable demo |
| CLI | `python main.py` | Terminal use, offline |

## Security Model

| Item | How it's handled |
|---|---|
| Master password | SHA-256 hashed, stored in `master.hash` |
| Encryption key | Fernet key stored in `secret.key` (local only, git-ignored) |
| Stored passwords | Fernet-encrypted in `passwords.txt` (local only, git-ignored) |
| Password input (CLI) | `getpass` — hidden from terminal |
| Password copy (web) | JS `navigator.clipboard` — copied in-browser, never exposed in HTML |
| Password copy (CLI) | `pyperclip` — copied to clipboard, not printed |

## Requirements

- Python 3.8+
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

## Usage

### Web Interface (Flask)

```bash
python app.py
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
  6. Exit
```

## Web Routes

| Route | Method | Description |
|---|---|---|
| `/` or `/login` | GET / POST | Master password login |
| `/setup` | GET / POST | First-run master password creation |
| `/logout` | GET | Clear session and log out |
| `/dashboard` | GET | View all saved entries |
| `/add` | GET / POST | Add a new entry |
| `/update/<service>` | GET / POST | Update an existing entry |
| `/delete/<service>` | POST | Delete an entry |
| `/view` | POST (JSON) | Return decrypted password (AJAX) |
| `/generate` | POST (JSON) | Generate a secure password (AJAX) |

## Deploy to Render

This repo ships with a `render.yaml` and `Procfile` for zero-config deployment on [Render](https://render.com).

### Steps

1. Fork or push this repo to your GitHub account.
2. Go to [https://dashboard.render.com](https://dashboard.render.com) and click **New → Web Service**.
3. Connect your GitHub repo (`Python-Password-Manager`).
4. Render will auto-detect `render.yaml` and pre-fill all settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Env var:** `FLASK_SECRET_KEY` auto-generated
   - **Disk:** 1 GB persistent volume mounted at `/opt/render/project/src` (keeps `secret.key`, `passwords.txt`, `master.hash` across deploys)
5. Click **Create Web Service**.
6. Once deployed, visit your Render URL (e.g. `https://python-password-manager.onrender.com`).
7. On first visit you will be prompted to create your master password.

### Railway (alternative)

1. Install the [Railway CLI](https://docs.railway.app/develop/cli): `npm install -g @railway/cli`
2. `railway login`
3. `railway init` and select this repo.
4. `railway up`
5. Set `FLASK_SECRET_KEY` in your Railway project environment variables.

> **Note:** The free tier on Render spins down after 15 minutes of inactivity. The first request after sleep may take ~30 seconds.

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
├── secret.key           # Fernet key (auto-generated, git-ignored)
├── passwords.txt        # Encrypted passwords (auto-generated, git-ignored)
└── master.hash          # SHA-256 master password hash (auto-generated, git-ignored)
```

## Roadmap

- Deploy web app to Render or Railway for public live demo
- Export / import encrypted vault backup
- Search entries by keyword
- 2FA / TOTP support
