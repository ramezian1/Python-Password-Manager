# Python Password Manager

A secure, CLI-based password manager written in Python. Passwords are encrypted with **Fernet** (AES-128) via the `cryptography` library. The master password is never stored in plain text — only its SHA-256 hash is saved locally.

## Features

- **Master password protection** — hashed with SHA-256, set on first run, never hardcoded
- **Add** passwords with a service/website, username, and password
- **Generate** cryptographically secure passwords (customizable length)
- **Find & copy** — retrieves a password and copies it silently to your clipboard via `pyperclip`
- **List all entries** — shows every saved service and username (no passwords displayed)
- **Update** an existing password (generate or manual)
- **Delete** an entry with confirmation prompt
- **Password strength checker** — enforces lowercase, uppercase, digit, and symbol
- **Fernet encryption** — all stored passwords are encrypted at rest
- **`.gitignore` protection** — `secret.key`, `passwords.txt`, and `master.hash` are excluded from version control

## Security Model

| Item | How it's handled |
|---|---|
| Master password | SHA-256 hashed, stored in `master.hash` |
| Encryption key | Fernet key stored in `secret.key` (local only, git-ignored) |
| Stored passwords | Fernet-encrypted in `passwords.txt` (local only, git-ignored) |
| Password input | `getpass` — hidden from terminal |
| Clipboard | `pyperclip` — password copied, not printed |

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

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

## Usage

```bash
python main.py
```

### First run

On first launch you will be prompted to create a master password (minimum 8 characters). The hash is saved to `master.hash`. You will never be asked to set it again unless that file is deleted.

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

#### 1. Add password
- Enter the service/website (e.g. `gmail.com`), username/email, then choose to generate a secure password or enter one manually.
- Manually entered passwords are checked for strength before saving.
- Generated passwords are copied to your clipboard automatically.

#### 2. Find / copy password
- Enter service and username. The decrypted password is copied to your clipboard — it is **not** printed to the terminal.

#### 3. List all entries
- Displays a numbered table of all saved services and usernames. No passwords are shown.

#### 4. Update password
- Enter service and username, then generate or enter a new password to replace the existing one.

#### 5. Delete entry
- Enter service and username. You must type `yes` to confirm deletion.

## File Structure

```
Python-Password-Manager/
├── main.py            # Main application
├── requirements.txt   # Python dependencies
├── .gitignore         # Excludes sensitive files
├── secret.key         # Fernet key (auto-generated, git-ignored)
├── passwords.txt      # Encrypted passwords (auto-generated, git-ignored)
└── master.hash        # SHA-256 master password hash (auto-generated, git-ignored)
```

## Roadmap

- Export/import encrypted vault backup
- Optional GUI (Tkinter)
- Password expiry reminders
- Search entries by keyword
