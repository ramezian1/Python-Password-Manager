import os
import re
import hashlib
import secrets
import string
import getpass
import pyperclip
from cryptography.fernet import Fernet

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
KEY_FILE = "secret.key"
PASSWORDS_FILE = "passwords.txt"
MASTER_HASH_FILE = "master.hash"


# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------

def generate_key():
    """Load or generate the Fernet encryption key."""
    if not os.path.exists(KEY_FILE):
        secret_key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(secret_key)
    else:
        with open(KEY_FILE, "rb") as f:
            secret_key = f.read()
    return secret_key


# ---------------------------------------------------------------------------
# Master password  (hashed with SHA-256, never stored in plain text)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Return a hex SHA-256 digest of the given password."""
    return hashlib.sha256(password.encode()).hexdigest()


def setup_master_password():
    """First-run: prompt the user to create a master password and store its hash."""
    print("\n=== First Run: Set Up Master Password ===")
    while True:
        pwd = getpass.getpass("Create master password: ")
        confirm = getpass.getpass("Confirm master password: ")
        if pwd != confirm:
            print("Passwords do not match. Try again.")
            continue
        if len(pwd) < 8:
            print("Master password must be at least 8 characters.")
            continue
        with open(MASTER_HASH_FILE, "w") as f:
            f.write(hash_password(pwd))
        print("Master password set successfully.")
        return


def verify_master_password() -> bool:
    """Prompt for the master password and verify it against the stored hash."""
    attempt = getpass.getpass("Enter master password: ")
    with open(MASTER_HASH_FILE, "r") as f:
        stored_hash = f.read().strip()
    return hash_password(attempt) == stored_hash


# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------

def encrypt_password(password: str, secret_key: bytes) -> str:
    """Encrypt a password and return it as a UTF-8 string."""
    cipher = Fernet(secret_key)
    return cipher.encrypt(password.encode()).decode("utf-8")


def decrypt_password(encrypted_str: str, secret_key: bytes) -> str:
    """Decrypt an encrypted password string and return plain text."""
    cipher = Fernet(secret_key)
    return cipher.decrypt(encrypted_str.encode("utf-8")).decode()


# ---------------------------------------------------------------------------
# Password strength & generation
# ---------------------------------------------------------------------------

def check_password_strength(password: str) -> bool:
    """Return True if password meets minimum complexity requirements."""
    if len(password) < 8:
        print("  Reason: Too short (minimum 8 characters).")
        return False
    if not re.search(r"[a-z]", password):
        print("  Reason: Needs at least one lowercase letter.")
        return False
    if not re.search(r"[A-Z]", password):
        print("  Reason: Needs at least one uppercase letter.")
        return False
    if not re.search(r"[0-9]", password):
        print("  Reason: Needs at least one digit.")
        return False
    if not re.search(r"[\W_]", password):
        print("  Reason: Needs at least one special character.")
        return False
    return True


def generate_secure_password(length: int = 16) -> str:
    """Generate a cryptographically secure password."""
    length = max(length, 8)
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    symbols = string.punctuation
    all_chars = lower + upper + digits + symbols
    # Guarantee at least one of each required type
    chars = [
        secrets.choice(lower),
        secrets.choice(upper),
        secrets.choice(digits),
        secrets.choice(symbols),
    ]
    chars += [secrets.choice(all_chars) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


# ---------------------------------------------------------------------------
# Storage: each line format  =>  service:username:encrypted_password
# ---------------------------------------------------------------------------

def _load_entries():
    """Return a list of (service, username, encrypted_password) tuples."""
    if not os.path.exists(PASSWORDS_FILE):
        return []
    entries = []
    with open(PASSWORDS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(":", 2)
            if len(parts) == 3:
                entries.append(tuple(parts))
            elif len(parts) == 2:
                # Backwards-compat: old format username:encrypted
                entries.append(("", parts[0], parts[1]))
    return entries


def _save_entries(entries):
    """Write all entries back to the passwords file."""
    with open(PASSWORDS_FILE, "w") as f:
        for service, username, enc in entries:
            f.write(f"{service}:{username}:{enc}\n")


def add_entry(service: str, username: str, password: str, secret_key: bytes):
    """Encrypt and save a new entry."""
    entries = _load_entries()
    # Check for duplicate
    for s, u, _ in entries:
        if s.lower() == service.lower() and u.lower() == username.lower():
            print(f"  Entry for '{username}' at '{service}' already exists. Use Update to change it.")
            return
    enc = encrypt_password(password, secret_key)
    entries.append((service, username, enc))
    _save_entries(entries)
    print("  Password saved securely.")


def find_entry(service: str, username: str, secret_key: bytes):
    """Return decrypted password for a given service+username, or None."""
    for s, u, enc in _load_entries():
        if s.lower() == service.lower() and u.lower() == username.lower():
            return decrypt_password(enc, secret_key)
    return None


def update_entry(service: str, username: str, new_password: str, secret_key: bytes):
    """Update the password for an existing entry."""
    entries = _load_entries()
    updated = False
    new_entries = []
    for s, u, enc in entries:
        if s.lower() == service.lower() and u.lower() == username.lower():
            new_entries.append((s, u, encrypt_password(new_password, secret_key)))
            updated = True
        else:
            new_entries.append((s, u, enc))
    if updated:
        _save_entries(new_entries)
        print("  Password updated successfully.")
    else:
        print("  Entry not found.")


def delete_entry(service: str, username: str):
    """Delete an entry for a given service+username."""
    entries = _load_entries()
    new_entries = [(s, u, enc) for s, u, enc in entries
                   if not (s.lower() == service.lower() and u.lower() == username.lower())]
    if len(new_entries) == len(entries):
        print("  Entry not found.")
    else:
        _save_entries(new_entries)
        print("  Entry deleted.")


def list_entries():
    """Print all stored service/username pairs (no passwords)."""
    entries = _load_entries()
    if not entries:
        print("  No entries stored yet.")
        return
    print(f"\n  {'#':<4} {'Service':<20} {'Username'}")
    print("  " + "-" * 44)
    for i, (s, u, _) in enumerate(entries, 1):
        service_display = s if s else "(none)"
        print(f"  {i:<4} {service_display:<20} {u}")


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main():
    # First-run setup
    if not os.path.exists(MASTER_HASH_FILE):
        setup_master_password()

    # Authenticate
    if not verify_master_password():
        print("\nIncorrect master password. Exiting.")
        return

    print("\nAccess granted.")

    # Load/generate encryption key
    secret_key = generate_key()

    while True:
        print("""
=== Password Manager ===""")
        print("  1. Add password")
        print("  2. Find / copy password")
        print("  3. List all entries")
        print("  4. Update password")
        print("  5. Delete entry")
        print("  6. Exit")

        choice_str = input("\nChoice (1-6): ").strip()

        try:
            choice = int(choice_str)
        except ValueError:
            print("Invalid input. Enter a number 1-6.")
            continue

        if choice == 1:
            service = input("  Service / website (e.g. gmail.com): ").strip()
            username = input("  Username / email: ").strip()
            gen = input("  Generate a secure password? (y/n): ").strip().lower()
            if gen == "y":
                try:
                    length = int(input("  Password length [16]: ").strip() or "16")
                except ValueError:
                    length = 16
                password = generate_secure_password(length)
                print(f"  Generated: {password}")
                try:
                    pyperclip.copy(password)
                    print("  (Copied to clipboard)")
                except Exception:
                    pass
                add_entry(service, username, password, secret_key)
            else:
                password = getpass.getpass("  Enter password: ")
                if check_password_strength(password):
                    add_entry(service, username, password, secret_key)
                else:
                    print("  Password does not meet strength requirements. Not saved.")

        elif choice == 2:
            service = input("  Service / website: ").strip()
            username = input("  Username / email: ").strip()
            result = find_entry(service, username, secret_key)
            if result:
                try:
                    pyperclip.copy(result)
                    print("  Password copied to clipboard (not displayed for security).")
                except Exception:
                    # Fallback if pyperclip unavailable
                    print(f"  Password: {result}")
            else:
                print("  Entry not found.")

        elif choice == 3:
            list_entries()

        elif choice == 4:
            service = input("  Service / website: ").strip()
            username = input("  Username / email: ").strip()
            gen = input("  Generate a new secure password? (y/n): ").strip().lower()
            if gen == "y":
                try:
                    length = int(input("  Password length [16]: ").strip() or "16")
                except ValueError:
                    length = 16
                new_password = generate_secure_password(length)
                print(f"  Generated: {new_password}")
                try:
                    pyperclip.copy(new_password)
                    print("  (Copied to clipboard)")
                except Exception:
                    pass
            else:
                new_password = getpass.getpass("  New password: ")
                if not check_password_strength(new_password):
                    print("  Password does not meet strength requirements. Not updated.")
                    continue
            update_entry(service, username, new_password, secret_key)

        elif choice == 5:
            service = input("  Service / website: ").strip()
            username = input("  Username / email: ").strip()
            confirm = input(f"  Delete entry for '{username}' at '{service}'? (yes/no): ").strip().lower()
            if confirm == "yes":
                delete_entry(service, username)
            else:
                print("  Cancelled.")

        elif choice == 6:
            print("Goodbye.")
            break

        else:
            print("Invalid choice. Enter a number 1-6.")


if __name__ == "__main__":
    main()
