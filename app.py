"""Flask front-end for the password manager.

The encryption key is derived from the master password at login and held in
memory only, in ``_UNLOCKED``, keyed by an opaque session id. It deliberately
does NOT go in the Flask session: session cookies are signed but not
encrypted, so anything put there is readable by the client.

Because the key lives in process memory, the app must run as a SINGLE worker
(see Procfile / render.yaml). With multiple workers a request can land on a
worker that never saw the login and the user appears randomly logged out.
"""

import os
import secrets
import time

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from main import (
    VaultError,
    add_entry,
    check_password_strength,
    create_vault,
    delete_entry,
    find_entry,
    generate_secure_password,
    legacy_vault_present,
    list_entries,
    migrate_legacy_vault,
    unlock_vault,
    update_entry,
    vault_exists,
)

# How long an unlocked vault stays unlocked without activity.
UNLOCK_TTL_SECONDS = 15 * 60

# Where the browser-session signing key is kept when running locally. This
# only signs session cookies; it is NOT the vault key and cannot unlock
# anything. A forged cookie yields a session id that is absent from _UNLOCKED,
# so it still gets you nothing.
SESSION_KEY_FILE = ".flask_secret"

# The normal case is local: clone the repo, run it, open a browser. Setting
# FLASK_SECRET_KEY is what marks a hosted deployment, where the app is served
# over HTTPS and the cookie can be locked down further.
HOSTED = bool(os.environ.get("FLASK_SECRET_KEY"))


def _local_session_key() -> str:
    """Read, or create once, a stable session key for local use.

    Stored in a file so restarting the program does not log you out. Falls
    back to a throwaway key if the file cannot be written (read-only checkout,
    awkward permissions) -- that still works, it just means a restart logs you
    out.
    """
    try:
        with open(SESSION_KEY_FILE, "r", encoding="utf-8") as handle:
            existing = handle.read().strip()
        if existing:
            return existing
    except OSError:
        pass

    key = secrets.token_hex(32)
    try:
        with open(SESSION_KEY_FILE, "w", encoding="utf-8") as handle:
            handle.write(key)
        os.chmod(SESSION_KEY_FILE, 0o600)
    except OSError:
        pass
    return key


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or _local_session_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    # Lax stops the cookie riding along on cross-site POSTs, which is what
    # guards /delete and /view here -- there is no CSRF token yet.
    SESSION_COOKIE_SAMESITE="Lax",
    # A Secure cookie is never sent over plain http, which would break login
    # on http://127.0.0.1. Only switch it on where there is real HTTPS.
    SESSION_COOKIE_SECURE=HOSTED,
)

# session id -> {"key": bytes, "expires": float}
_UNLOCKED: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Session / key handling
# ---------------------------------------------------------------------------

def _purge_expired(now: float) -> None:
    for sid in [s for s, v in _UNLOCKED.items() if v["expires"] <= now]:
        _UNLOCKED.pop(sid, None)


def _store_key(key: bytes) -> None:
    sid = secrets.token_urlsafe(32)
    session.clear()
    session["sid"] = sid
    # Only used by base.html to decide whether to show the nav links.
    session["authenticated"] = True
    _UNLOCKED[sid] = {"key": key, "expires": time.time() + UNLOCK_TTL_SECONDS}


def _forget_key() -> None:
    sid = session.get("sid")
    if sid:
        _UNLOCKED.pop(sid, None)
    session.clear()


def current_key() -> bytes | None:
    """Return the unlocked key for this session, refreshing its idle timer."""
    now = time.time()
    _purge_expired(now)
    sid = session.get("sid")
    if not sid:
        return None
    record = _UNLOCKED.get(sid)
    if record is None:
        session.clear()
        return None
    record["expires"] = now + UNLOCK_TTL_SECONDS
    return record["key"]


def _wants_json() -> bool:
    return request.accept_mimetypes.best == "application/json" or request.is_json


@app.errorhandler(VaultError)
def handle_vault_error(exc: VaultError):
    if _wants_json():
        return jsonify({"error": str(exc)}), 500
    flash(str(exc), "error")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Setup: first-run master password creation
# ---------------------------------------------------------------------------

@app.route("/setup", methods=["GET", "POST"])
def setup():
    if vault_exists() or legacy_vault_present():
        return redirect(url_for("login"))

    if request.method == "POST":
        pwd = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        ok, reason = check_password_strength(pwd)
        if pwd != confirm:
            flash("Passwords do not match.", "error")
        elif not ok:
            flash(reason, "error")
        else:
            create_vault(pwd)
            flash("Vault created. Please log in.", "success")
            return redirect(url_for("login"))

    return render_template("setup.html")


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if not vault_exists() and not legacy_vault_present():
        return redirect(url_for("setup"))
    if current_key() is not None:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        pwd = request.form.get("password", "")

        if legacy_vault_present():
            # First login after the upgrade: re-encrypt under a derived key.
            try:
                key, count, skipped = migrate_legacy_vault(pwd)
            except VaultError as exc:
                flash(str(exc), "error")
                return render_template("login.html")
            _store_key(key)
            flash(
                f"Vault upgraded and re-encrypted ({count} "
                f"entr{'y' if count == 1 else 'ies'}). Your old secret.key was "
                "renamed to secret.key.migrated -- delete it.",
                "success",
            )
            if skipped:
                flash(
                    f"{skipped} entr{'y' if skipped == 1 else 'ies'} could not be "
                    "decrypted and were left behind in passwords.txt.migrated.",
                    "warning",
                )
            return redirect(url_for("dashboard"))

        key = unlock_vault(pwd)
        if key is not None:
            _store_key(key)
            return redirect(url_for("dashboard"))
        flash("Incorrect master password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    _forget_key()
    flash("Logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard")
def dashboard():
    if current_key() is None:
        return redirect(url_for("login"))
    return render_template("dashboard.html", entries=list_entries())


# ---------------------------------------------------------------------------
# Add entry
# ---------------------------------------------------------------------------

def _requested_length() -> int:
    """Clamp the generator length to the range the form advertises."""
    try:
        length = int(request.form.get("length", 16))
    except (TypeError, ValueError):
        length = 16
    return max(8, min(length, 64))


@app.route("/add", methods=["GET", "POST"])
def add():
    key = current_key()
    if key is None:
        return redirect(url_for("login"))

    service = username = ""
    if request.method == "POST":
        service = request.form.get("service", "").strip()
        username = request.form.get("username", "").strip()

        if request.form.get("action") == "generate":
            return render_template(
                "add.html",
                generated=generate_secure_password(_requested_length()),
                service=service,
                username=username,
            )

        password = request.form.get("password", "").strip()
        if not service or not username or not password:
            flash("All fields are required.", "error")
        else:
            ok, reason = check_password_strength(password)
            if not ok:
                # A warning, not a block: it is the user's password to choose.
                flash(f"Weak password saved: {reason}", "warning")
            if add_entry(service, username, password, key):
                flash(f'Entry for "{service}" added.', "success")
                return redirect(url_for("dashboard"))
            flash(
                f'"{username}" at "{service}" already exists. Edit it instead.',
                "error",
            )

    return render_template("add.html", service=service, username=username)


# ---------------------------------------------------------------------------
# View a password (AJAX; dashboard.html posts form-encoded, not JSON)
# ---------------------------------------------------------------------------

@app.route("/view", methods=["POST"])
def view():
    key = current_key()
    if key is None:
        return jsonify({"error": "Unauthorized"}), 401

    entry = find_entry(
        request.form.get("service", ""), request.form.get("username", ""), key
    )
    if entry is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"password": entry["password"]})


# ---------------------------------------------------------------------------
# Update entry
#
# Identified by query string rather than a path segment: a service name can be
# empty or contain a slash, both of which break /update/<service>/<username>.
# ---------------------------------------------------------------------------

@app.route("/update", methods=["GET", "POST"])
def update():
    key = current_key()
    if key is None:
        return redirect(url_for("login"))

    source = request.form if request.method == "POST" else request.args
    service = source.get("service", "")
    username = source.get("username", "")

    entry = find_entry(service, username, key)
    if entry is None:
        flash("Entry not found.", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        if request.form.get("action") == "generate":
            return render_template(
                "update.html",
                service=service,
                username=username,
                generated=generate_secure_password(_requested_length()),
            )

        new_password = request.form.get("password", "").strip()
        if not new_password:
            flash("Password cannot be empty.", "error")
        else:
            ok, reason = check_password_strength(new_password)
            if not ok:
                flash(f"Weak password saved: {reason}", "warning")
            if update_entry(service, username, new_password, key):
                flash(f'Password for "{service}" updated.', "success")
            else:
                flash("Entry not found.", "error")
            return redirect(url_for("dashboard"))

    return render_template("update.html", service=service, username=username)


# ---------------------------------------------------------------------------
# Delete entry
# ---------------------------------------------------------------------------

@app.route("/delete", methods=["POST"])
def delete():
    if current_key() is None:
        return redirect(url_for("login"))

    service = request.form.get("service", "")
    username = request.form.get("username", "")
    if delete_entry(service, username):
        flash(f'Entry "{service}" deleted.', "success")
    else:
        flash("Entry not found.", "error")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Generate password (AJAX)
# ---------------------------------------------------------------------------

@app.route("/generate", methods=["POST"])
def generate():
    if current_key() is None:
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    try:
        length = int(payload.get("length", 16))
    except (TypeError, ValueError):
        length = 16
    return jsonify({"password": generate_secure_password(max(8, min(length, 64)))})


if __name__ == "__main__":
    # Loopback by default. This is a personal vault on your own machine;
    # binding 0.0.0.0 would offer the login page to everyone on your network.
    # Hosting platforms run this through gunicorn and do their own binding.
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    print(f"Password manager running at http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
