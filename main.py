"""Core vault logic for the password manager.

Design notes
------------
* The Fernet encryption key is *derived* from the master password with scrypt
  and is never written to disk. An attacker who steals ``vault.json`` gets a
  salt, a verifier and a pile of ciphertext -- nothing that decrypts without
  the master password. (The previous design stored the key in ``secret.key``
  right next to the data, which made the encryption decorative.)
* Nothing in this module prompts or prints. Both the CLI at the bottom of this
  file and the Flask app in ``app.py`` drive the same functions; they return
  values and the caller decides how to report them.
"""

import base64
import getpass
import hashlib
import hmac
import json
import os
import re
import secrets
import string
import tempfile

from cryptography.fernet import Fernet, InvalidToken

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
VAULT_FILE = "vault.json"
VAULT_VERSION = 2

# Pre-v2 layout, kept only so existing vaults can be migrated on first unlock.
LEGACY_KEY_FILE = "secret.key"
LEGACY_PASSWORDS_FILE = "passwords.txt"
LEGACY_MASTER_HASH_FILE = "master.hash"

# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------
# scrypt "interactive" parameters: n=2**14, r=8, p=1 costs ~16 MB and ~0.1s,
# which is tolerable on a small web dyno while being far more expensive to
# brute-force than the bare SHA-256 this replaced.
SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 64 * 1024 * 1024
SALT_BYTES = 16


class VaultError(Exception):
    """Raised when the vault is missing, malformed, or already exists."""


def _b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def derive_key(password: str, salt: bytes, n: int = SCRYPT_N, r: int = SCRYPT_R,
               p: int = SCRYPT_P) -> tuple[bytes, bytes]:
    """Derive (fernet_key, verifier) from a master password.

    64 bytes are stretched out of scrypt and split: the first 32 become the
    encryption key, the last 32 are stored on disk as a verifier. Storing the
    second half lets us check a password without revealing anything about the
    first half.
    """
    material = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=64,
        maxmem=SCRYPT_MAXMEM,
    )
    fernet_key = base64.urlsafe_b64encode(material[:32])
    verifier = material[32:]
    return fernet_key, verifier


# ---------------------------------------------------------------------------
# Vault file I/O
# ---------------------------------------------------------------------------

def _restrict_permissions(path: str) -> None:
    """Best-effort owner-only permissions. A no-op where they do not apply."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _atomic_write(path: str, text: str) -> None:
    """Write via a temp file + rename so an interrupted save cannot truncate
    the vault. Losing a password vault to a crash mid-write is unacceptable."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".vault-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        _restrict_permissions(tmp)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def vault_exists() -> bool:
    return os.path.exists(VAULT_FILE)


def _load_vault() -> dict:
    if not vault_exists():
        raise VaultError("No vault found. Create one first.")
    try:
        with open(VAULT_FILE, "r", encoding="utf-8") as handle:
            vault = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise VaultError(f"Vault file is unreadable: {exc}") from exc
    if vault.get("version") != VAULT_VERSION:
        raise VaultError(f"Unsupported vault version: {vault.get('version')!r}")
    return vault


def _save_vault(vault: dict) -> None:
    _atomic_write(VAULT_FILE, json.dumps(vault, indent=2, ensure_ascii=False))


def _new_vault(master_password: str) -> tuple[dict, bytes]:
    salt = secrets.token_bytes(SALT_BYTES)
    key, verifier = derive_key(master_password, salt)
    vault = {
        "version": VAULT_VERSION,
        "kdf": {
            "name": "scrypt",
            "salt": _b64e(salt),
            "n": SCRYPT_N,
            "r": SCRYPT_R,
            "p": SCRYPT_P,
        },
        "verifier": _b64e(verifier),
        "entries": [],
    }
    return vault, key


# ---------------------------------------------------------------------------
# Master password
# ---------------------------------------------------------------------------

def create_vault(master_password: str) -> bytes:
    """Create an empty vault and return the derived encryption key."""
    if vault_exists():
        raise VaultError("A vault already exists.")
    vault, key = _new_vault(master_password)
    _save_vault(vault)
    return key


def unlock_vault(master_password: str) -> bytes | None:
    """Return the derived key if the password is correct, else None."""
    vault = _load_vault()
    kdf = vault["kdf"]
    key, verifier = derive_key(
        master_password, _b64d(kdf["salt"]), kdf["n"], kdf["r"], kdf["p"]
    )
    # Constant-time compare: a plain == leaks timing information.
    if hmac.compare_digest(verifier, _b64d(vault["verifier"])):
        return key
    return None


def change_master_password(old_password: str, new_password: str) -> bytes | None:
    """Re-key the vault under a new master password.

    Every entry is decrypted with the old key and re-encrypted with the new
    one, under a fresh salt. Returns the new key, or None if ``old_password``
    is wrong.
    """
    old_key = unlock_vault(old_password)
    if old_key is None:
        return None

    old_cipher = Fernet(old_key)
    plaintexts = [
        (entry["service"], entry["username"],
         old_cipher.decrypt(entry["password"].encode("utf-8")).decode())
        for entry in _load_vault()["entries"]
    ]

    vault, new_key = _new_vault(new_password)
    new_cipher = Fernet(new_key)
    vault["entries"] = [
        {
            "service": service,
            "username": username,
            "password": new_cipher.encrypt(password.encode()).decode("utf-8"),
        }
        for service, username, password in plaintexts
    ]
    _save_vault(vault)
    return new_key


# ---------------------------------------------------------------------------
# Password strength & generation
# ---------------------------------------------------------------------------

def check_password_strength(password: str) -> tuple[bool, str]:
    """Return (ok, reason). ``reason`` is empty when the password passes."""
    if len(password) < 8:
        return False, "Too short (minimum 8 characters)."
    if not re.search(r"[a-z]", password):
        return False, "Needs at least one lowercase letter."
    if not re.search(r"[A-Z]", password):
        return False, "Needs at least one uppercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Needs at least one digit."
    if not re.search(r"[\W_]", password):
        return False, "Needs at least one special character."
    return True, ""


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
# Entries
#
# An entry is identified by the (service, username) pair, compared
# case-insensitively -- one service can hold several accounts.
# ---------------------------------------------------------------------------

def _matches(entry: dict, service: str, username: str) -> bool:
    return (entry["service"].lower() == service.lower()
            and entry["username"].lower() == username.lower())


def list_entries() -> list[dict]:
    """Return [{'service', 'username'}, ...]. No key needed: only passwords
    are encrypted, so listing never has to unlock anything."""
    return [
        {"service": entry["service"], "username": entry["username"]}
        for entry in _load_vault()["entries"]
    ]


def add_entry(service: str, username: str, password: str, key: bytes) -> bool:
    """Encrypt and store a new entry. Returns False if it already exists."""
    vault = _load_vault()
    if any(_matches(entry, service, username) for entry in vault["entries"]):
        return False
    vault["entries"].append({
        "service": service,
        "username": username,
        "password": Fernet(key).encrypt(password.encode()).decode("utf-8"),
    })
    _save_vault(vault)
    return True


def find_entry(service: str, username: str, key: bytes) -> dict | None:
    """Return {'service', 'username', 'password'} with the password decrypted."""
    for entry in _load_vault()["entries"]:
        if _matches(entry, service, username):
            try:
                plain = Fernet(key).decrypt(
                    entry["password"].encode("utf-8")).decode()
            except InvalidToken as exc:
                raise VaultError(
                    "Entry could not be decrypted with this key."
                ) from exc
            return {
                "service": entry["service"],
                "username": entry["username"],
                "password": plain,
            }
    return None


def update_entry(service: str, username: str, new_password: str, key: bytes) -> bool:
    """Replace the password of an existing entry. False if it does not exist."""
    vault = _load_vault()
    for entry in vault["entries"]:
        if _matches(entry, service, username):
            entry["password"] = Fernet(key).encrypt(
                new_password.encode()).decode("utf-8")
            _save_vault(vault)
            return True
    return False


def delete_entry(service: str, username: str) -> bool:
    """Remove an entry. False if it does not exist."""
    vault = _load_vault()
    remaining = [e for e in vault["entries"] if not _matches(e, service, username)]
    if len(remaining) == len(vault["entries"]):
        return False
    vault["entries"] = remaining
    _save_vault(vault)
    return True


# ---------------------------------------------------------------------------
# Migration from the pre-v2 layout
#
# Old layout: master.hash (bare SHA-256), secret.key (raw Fernet key on disk)
# and passwords.txt with "service:username:ciphertext" lines.
# ---------------------------------------------------------------------------

def legacy_vault_present() -> bool:
    return not vault_exists() and os.path.exists(LEGACY_PASSWORDS_FILE)


def _load_legacy_entries() -> list[tuple[str, str, str]]:
    if not os.path.exists(LEGACY_PASSWORDS_FILE):
        return []
    entries = []
    with open(LEGACY_PASSWORDS_FILE, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            parts = line.split(":", 2)
            if len(parts) == 3:
                entries.append((parts[0], parts[1], parts[2]))
            elif len(parts) == 2:
                # Even older format: username:ciphertext, no service.
                entries.append(("", parts[0], parts[1]))
    return entries


def verify_legacy_master_password(password: str) -> bool:
    """Check a password against the old unsalted SHA-256 ``master.hash``."""
    if not os.path.exists(LEGACY_MASTER_HASH_FILE):
        # No hash to check against; accept and let it become the new master.
        return True
    with open(LEGACY_MASTER_HASH_FILE, "r", encoding="utf-8") as handle:
        stored = handle.read().strip()
    return hmac.compare_digest(
        hashlib.sha256(password.encode()).hexdigest(), stored
    )


def migrate_legacy_vault(master_password: str) -> tuple[bytes, int, int]:
    """Convert a pre-v2 vault to the derived-key format.

    Returns (key, migrated, skipped). Lines that will not decrypt are skipped
    rather than aborting the whole migration, but they are counted and
    reported -- the old ``service:username:ciphertext`` format silently
    corrupts any entry whose service or username contains a colon, so a
    non-zero ``skipped`` usually means such an entry was already unreadable.

    The old files are renamed to ``*.migrated`` rather than deleted, so a bad
    migration is recoverable -- but they still contain the old on-disk key and
    should be deleted once the new vault is confirmed working.
    """
    if not verify_legacy_master_password(master_password):
        raise VaultError("Incorrect master password.")
    if not os.path.exists(LEGACY_KEY_FILE):
        raise VaultError(f"Cannot migrate: {LEGACY_KEY_FILE} is missing.")

    with open(LEGACY_KEY_FILE, "rb") as handle:
        old_cipher = Fernet(handle.read())

    vault, key = _new_vault(master_password)
    new_cipher = Fernet(key)
    skipped = 0
    for service, username, ciphertext in _load_legacy_entries():
        try:
            plain = old_cipher.decrypt(ciphertext.encode("utf-8")).decode()
        except InvalidToken:
            # Skip rather than abort: one corrupt line should not cost the
            # whole vault. The caller reports the count so it is never silent.
            skipped += 1
            continue
        vault["entries"].append({
            "service": service,
            "username": username,
            "password": new_cipher.encrypt(plain.encode()).decode("utf-8"),
        })
    _save_vault(vault)

    for path in (LEGACY_KEY_FILE, LEGACY_PASSWORDS_FILE, LEGACY_MASTER_HASH_FILE):
        if os.path.exists(path):
            os.replace(path, path + ".migrated")

    return key, len(vault["entries"]), skipped


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _prompt_new_master_password() -> str:
    while True:
        pwd = getpass.getpass("Create master password: ")
        confirm = getpass.getpass("Confirm master password: ")
        if pwd != confirm:
            print("Passwords do not match. Try again.")
            continue
        ok, reason = check_password_strength(pwd)
        if not ok:
            print(f"  {reason}")
            continue
        return pwd


def _copy_to_clipboard(text: str) -> bool:
    try:
        import pyperclip

        pyperclip.copy(text)
        print("  (Copied to clipboard)")
        return True
    except Exception:
        # pyperclip is optional and needs a system clipboard; headless is fine.
        return False


def _prompt_password_for_entry(prompt: str) -> str | None:
    """Ask for a password or offer to generate one. None means 'rejected'."""
    if input("  Generate a secure password? (y/n): ").strip().lower() == "y":
        try:
            length = int(input("  Password length [16]: ").strip() or "16")
        except ValueError:
            length = 16
        password = generate_secure_password(length)
        print(f"  Generated: {password}")
        _copy_to_clipboard(password)
        return password

    password = getpass.getpass(prompt)
    ok, reason = check_password_strength(password)
    if not ok:
        print(f"  Reason: {reason}")
        print("  Password does not meet strength requirements.")
        return None
    return password


def _unlock_or_create() -> bytes | None:
    """Bring the vault to an unlocked state, migrating or creating as needed."""
    if legacy_vault_present():
        print("\nAn old-format vault was found. Migrating to derived-key format.")
        pwd = getpass.getpass("Enter your existing master password: ")
        try:
            key, count, skipped = migrate_legacy_vault(pwd)
        except VaultError as exc:
            print(f"\n{exc}")
            return None
        print(f"Migrated {count} entr{'y' if count == 1 else 'ies'}.")
        if skipped:
            print(f"WARNING: {skipped} entr{'y' if skipped == 1 else 'ies'} could "
                  "not be decrypted and were left behind in passwords.txt.migrated.")
        print("The old secret.key/passwords.txt are renamed to *.migrated --")
        print("delete them once you have confirmed the vault works.")
        return key

    if not vault_exists():
        print("\n=== First Run: Set Up Master Password ===")
        print("This password derives your encryption key. There is no recovery.")
        return create_vault(_prompt_new_master_password())

    key = unlock_vault(getpass.getpass("Enter master password: "))
    if key is None:
        print("\nIncorrect master password. Exiting.")
    return key


def main():
    try:
        key = _unlock_or_create()
    except VaultError as exc:
        print(f"\n{exc}")
        return
    if key is None:
        return

    print("\nAccess granted.")

    while True:
        print("\n=== Password Manager ===")
        print("  1. Add password")
        print("  2. Find / copy password")
        print("  3. List all entries")
        print("  4. Update password")
        print("  5. Delete entry")
        print("  6. Change master password")
        print("  7. Exit")

        choice = input("\nChoice (1-7): ").strip()

        try:
            if choice == "1":
                service = input("  Service / website (e.g. gmail.com): ").strip()
                username = input("  Username / email: ").strip()
                password = _prompt_password_for_entry("  Enter password: ")
                if password is None:
                    print("  Not saved.")
                elif add_entry(service, username, password, key):
                    print("  Password saved securely.")
                else:
                    print(f"  Entry for '{username}' at '{service}' already exists.")

            elif choice == "2":
                service = input("  Service / website: ").strip()
                username = input("  Username / email: ").strip()
                entry = find_entry(service, username, key)
                if entry is None:
                    print("  Entry not found.")
                elif _copy_to_clipboard(entry["password"]):
                    print("  Password copied to clipboard (not displayed).")
                else:
                    print(f"  Password: {entry['password']}")

            elif choice == "3":
                entries = list_entries()
                if not entries:
                    print("  No entries stored yet.")
                else:
                    print(f"\n  {'#':<4} {'Service':<20} {'Username'}")
                    print("  " + "-" * 44)
                    for i, entry in enumerate(entries, 1):
                        service = entry["service"] or "(none)"
                        print(f"  {i:<4} {service:<20} {entry['username']}")

            elif choice == "4":
                service = input("  Service / website: ").strip()
                username = input("  Username / email: ").strip()
                password = _prompt_password_for_entry("  New password: ")
                if password is None:
                    print("  Not updated.")
                elif update_entry(service, username, password, key):
                    print("  Password updated successfully.")
                else:
                    print("  Entry not found.")

            elif choice == "5":
                service = input("  Service / website: ").strip()
                username = input("  Username / email: ").strip()
                confirm = input(
                    f"  Delete entry for '{username}' at '{service}'? (yes/no): "
                ).strip().lower()
                if confirm != "yes":
                    print("  Cancelled.")
                elif delete_entry(service, username):
                    print("  Entry deleted.")
                else:
                    print("  Entry not found.")

            elif choice == "6":
                current = getpass.getpass("  Current master password: ")
                new_key = change_master_password(
                    current, _prompt_new_master_password())
                if new_key is None:
                    print("  Incorrect master password.")
                else:
                    key = new_key
                    print("  Master password changed; vault re-encrypted.")

            elif choice == "7":
                print("Goodbye.")
                break

            else:
                print("Invalid choice. Enter a number 1-7.")

        except VaultError as exc:
            print(f"  {exc}")


if __name__ == "__main__":
    main()
