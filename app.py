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
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

# Load encryption key once at startup
SECRET_KEY = generate_key()


def is_authenticated():
    return session.get('authenticated') is True


# ------------------------------------------------------------------
# Setup: first-run master password creation via web
# ------------------------------------------------------------------

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
            ok, msg = check_password_strength(pwd)
            if not ok:
                flash(msg, 'error')
            else:
                setup_master_password(pwd)
                flash('Master password created. Please log in.', 'success')
                return redirect(url_for('login'))
    return render_template('setup.html')


# ------------------------------------------------------------------
# Login / Logout
# ------------------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if not os.path.exists(MASTER_HASH_FILE):
        return redirect(url_for('setup'))
    if is_authenticated():
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        stored = open(MASTER_HASH_FILE).read().strip()
        if hash_password(pwd) == stored:
            session['authenticated'] = True
            return redirect(url_for('dashboard'))
        flash('Incorrect master password.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

@app.route('/dashboard')
def dashboard():
    if not is_authenticated():
        return redirect(url_for('login'))
    entries = get_entries(SECRET_KEY)
    return render_template('dashboard.html', entries=entries)


# ------------------------------------------------------------------
# Add entry
# ------------------------------------------------------------------

@app.route('/add', methods=['GET', 'POST'])
def add():
    if not is_authenticated():
        return redirect(url_for('login'))
    generated = None
    if request.method == 'POST':
        action = request.form.get('action', 'save')
        if action == 'generate':
            length = int(request.form.get('length', 16))
            generated = generate_secure_password(length)
            return render_template('add.html', generated=generated,
                                   service=request.form.get('service', ''),
                                   username=request.form.get('username', ''))
        service = request.form.get('service', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not service or not username or not password:
            flash('All fields are required.', 'error')
        else:
            ok, msg = check_password_strength(password)
            if not ok:
                flash(f'Weak password: {msg}', 'warning')
            add_entry(SECRET_KEY, service, username, password)
            flash(f'Entry for "{service}" added.', 'success')
            return redirect(url_for('dashboard'))
    return render_template('add.html', generated=generated)


# ------------------------------------------------------------------
# View (AJAX – returns decrypted password JSON)
# ------------------------------------------------------------------

@app.route('/view', methods=['POST'])
def view():
    if not is_authenticated():
        return {'error': 'Unauthorized'}, 401
    service = request.json.get('service', '')
    result = find_entry(SECRET_KEY, service)
    if result:
        return {'password': result['password']}
    return {'error': 'Not found'}, 404


# ------------------------------------------------------------------
# Update entry
# ------------------------------------------------------------------

@app.route('/update/<service>', methods=['GET', 'POST'])
def update(service):
    if not is_authenticated():
        return redirect(url_for('login'))
    entry = find_entry(SECRET_KEY, service)
    if not entry:
        flash('Entry not found.', 'error')
        return redirect(url_for('dashboard'))
    generated = None
    if request.method == 'POST':
        action = request.form.get('action', 'save')
        if action == 'generate':
            length = int(request.form.get('length', 16))
            generated = generate_secure_password(length)
            return render_template('update.html', entry=entry, generated=generated)
        new_password = request.form.get('password', '').strip()
        if not new_password:
            flash('Password cannot be empty.', 'error')
        else:
            ok, msg = check_password_strength(new_password)
            if not ok:
                flash(f'Weak password: {msg}', 'warning')
            update_entry(SECRET_KEY, service, new_password)
            flash(f'Password for "{service}" updated.', 'success')
            return redirect(url_for('dashboard'))
    return render_template('update.html', entry=entry, generated=generated)


# ------------------------------------------------------------------
# Delete entry
# ------------------------------------------------------------------

@app.route('/delete/<service>', methods=['POST'])
def delete(service):
    if not is_authenticated():
        return redirect(url_for('login'))
    delete_entry(SECRET_KEY, service)
    flash(f'Entry "{service}" deleted.', 'success')
    return redirect(url_for('dashboard'))


# ------------------------------------------------------------------
# Generate password (AJAX)
# ------------------------------------------------------------------

@app.route('/generate', methods=['POST'])
def generate():
    if not is_authenticated():
        return {'error': 'Unauthorized'}, 401
    length = int(request.json.get('length', 16))
    password = generate_secure_password(length)
    return {'password': password}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
