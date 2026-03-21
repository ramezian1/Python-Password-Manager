# Python Password Manager

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
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/ramezian1/Python-Password-Manager.git
   cd Python-Password-Manager
   ```

2. (Recommended) Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage — Web Interface (Flask)

```bash
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

### First run
On first launch you'll be redirected to `/setup` to create your master password. The hash is saved to `master.hash`. Subsequent visits go straight to the login page.

### Pages

| Route | Description |
|---|---|
| `/` or `/login` | Master password login |
| `/setup` | First-run master password creation |
| `/dashboard` | Vault — list all entries with Copy / Edit / Delete |
| `/add` | Add a new entry (manual or generated password) |
| `/update` | Update an existing entry |

### Copy password
Click the **Copy** button on the dashboard. The decrypted password is sent via a secure AJAX request and written to your clipboard using `navigator.clipboard` — it is never rendered in the HTML.

## Usage — CLI

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

## File Structure

```
Python-Password-Manager/
├── app.py               # Flask web application
├── main.py              # CLI application + shared core logic
├── requirements.txt     # Python dependencies
├── .gitignore           # Excludes sensitive files
├── templates/
│   ├── base.html          # Shared layout (navbar, flash messages)
│   ├── login.html         # Master password login page
│   ├── setup.html         # First-run setup page
│   ├── dashboard.html     # Vault table with actions
│   ├── add.html           # Add entry form
│   └── update.html        # Update entry form
├── static/
│   └── style.css          # Dark theme styles
├── secret.key           # Fernet key (auto-generated, git-ignored)
├── passwords.txt        # Encrypted passwords (auto-generated, git-ignored)
└── master.hash          # SHA-256 master password hash (auto-generated, git-ignored)
```

## Roadmap

- Deploy web app to Render or Railway for public live demo
- Export / import encrypted vault backup
- Search entries by keyword
- Password expiry reminders
- Optional GUI (Tkinter)
