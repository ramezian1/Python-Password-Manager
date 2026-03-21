import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, flash
from main import (
    hash_password,
    generate_key,
    generate_secure_password,
    check_password_strength,
    add_entry,
    find_entry,
    update_entry,
    delete_entry,
    list_entries as get_entries,
    setup_master_password,
    MASTER_HASH_FILE,
)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Load encryption key once at startup
SECRET_KEY = generate_key()


def is_authenticated():
    return session.get('authenticated') is True


# ---------------------------------------------------------------------------
# Setup: first-run master password creation via web
# ---------------------------------------------------------------------------

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if os.path.exists(MASTER_HASH_FILE):
        return redirect(url_for('login'))
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        if pwd != confirm:
            flash('Passwords do not match.', 'error')
        elif len(pwd) < 8:
            flash('Master password must be at least 8 characters.', 'error')
        else:
            with open(MASTER_HASH_FILE, 'w') as f:
                f.write(hash_password(pwd))
            flash('Master password created. Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('setup.html')


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if not os.path.exists(MASTER_HASH_FILE):
        return redirect(url_for('setup'))
    if is_authenticated():
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        with open(MASTER_HASH_FILE, 'r') as f:
            stored = f.read().strip()
        if hash_password(pwd) == stored:
            session['authenticated'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Incorrect master password.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# Dashboard (list all entries)
# ---------------------------------------------------------------------------

@app.route('/dashboard')
def dashboard():
    if not is_authenticated():
        return redirect(url_for('login'))
    entries = get_entries()
    # entries is list of (service, username, encrypted) — strip encrypted for display
    visible = [{'service': s, 'username': u} for s, u, _ in entries]
    return render_template('dashboard.html', entries=visible)


# ---------------------------------------------------------------------------
# Add entry
# ---------------------------------------------------------------------------

@app.route('/add', methods=['GET', 'POST'])
def add():
    if not is_authenticated():
        return redirect(url_for('login'))
    generated = None
    if request.method == 'POST':
        service = request.form.get('service', '').strip()
        username = request.form.get('username', '').strip()
        action = request.form.get('action', '')
        if action == 'generate':
            try:
                length = int(request.form.get('length', 16))
            except ValueError:
                length = 16
            generated = generate_secure_password(length)
            return render_template('add.html', generated=generated,
                                   service=service, username=username)
        password = request.form.get('password', '').strip()
        if not service or not username or not password:
            flash('Service, username, and password are all required.', 'error')
        elif not check_password_strength(password):
            flash('Password too weak. Use uppercase, lowercase, digit, and symbol (min 8 chars).', 'error')
        else:
            add_entry(service, username, password, SECRET_KEY)
            flash(f'Entry for {username} @ {service} saved.', 'success')
            return redirect(url_for('dashboard'))
    return render_template('add.html', generated=generated)


# ---------------------------------------------------------------------------
# View / copy entry (returns password in response for JS copy)
# ---------------------------------------------------------------------------

@app.route('/view', methods=['POST'])
def view():
    if not is_authenticated():
        return {'error': 'Not authenticated'}, 401
    service = request.form.get('service', '').strip()
    username = request.form.get('username', '').strip()
    result = find_entry(service, username, SECRET_KEY)
    if result:
        return {'password': result}
    return {'error': 'Entry not found'}, 404


# ---------------------------------------------------------------------------
# Update entry
# ---------------------------------------------------------------------------

@app.route('/update', methods=['GET', 'POST'])
def update():
    if not is_authenticated():
        return redirect(url_for('login'))
    generated = None
    prefill_service = request.args.get('service', '')
    prefill_username = request.args.get('username', '')
    if request.method == 'POST':
        service = request.form.get('service', '').strip()
        username = request.form.get('username', '').strip()
        action = request.form.get('action', '')
        if action == 'generate':
            try:
                length = int(request.form.get('length', 16))
            except ValueError:
                length = 16
            generated = generate_secure_password(length)
            return render_template('update.html', generated=generated,
                                   service=service, username=username)
        password = request.form.get('password', '').strip()
        if not service or not username or not password:
            flash('All fields required.', 'error')
        elif not check_password_strength(password):
            flash('Password too weak. Use uppercase, lowercase, digit, and symbol (min 8 chars).', 'error')
        else:
            update_entry(service, username, password, SECRET_KEY)
            flash(f'Password updated for {username} @ {service}.', 'success')
            return redirect(url_for('dashboard'))
    return render_template('update.html', generated=generated,
                           service=prefill_service, username=prefill_username)


# ---------------------------------------------------------------------------
# Delete entry
# ---------------------------------------------------------------------------

@app.route('/delete', methods=['POST'])
def delete():
    if not is_authenticated():
        return redirect(url_for('login'))
    service = request.form.get('service', '').strip()
    username = request.form.get('username', '').strip()
    delete_entry(service, username)
    flash(f'Entry for {username} @ {service} deleted.', 'success')
    return redirect(url_for('dashboard'))


# ---------------------------------------------------------------------------
# Generate password (standalone AJAX endpoint)
# ---------------------------------------------------------------------------

@app.route('/generate', methods=['POST'])
def generate():
    if not is_authenticated():
        return {'error': 'Not authenticated'}, 401
    try:
        length = int(request.form.get('length', 16))
    except ValueError:
        length = 16
    pwd = generate_secure_password(length)
    return {'password': pwd}


if __name__ == '__main__':
    app.run(debug=True)
