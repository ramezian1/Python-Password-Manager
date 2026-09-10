# Python Password Manager

A place to keep your passwords. You remember one master password, and the program remembers the rest for you — scrambled, so the file on your computer is unreadable to anyone who doesn't know your master password.

**This runs on your own computer.** You download it, run it, and your passwords stay on your machine. Nothing is sent anywhere, there's no account to sign up for, and no server sees your data. The "web" version just means the screen you use opens in your browser instead of a terminal window — it's still your own computer talking to itself.

It comes in two flavours: a web page you open in your browser, and a text menu you use in a terminal. Both work on the same saved passwords.

---

## How it works, step by step

**1. You pick one master password.**
The first time you run the program, it asks you to choose a master password. This is the only one you have to remember.

**2. The program turns that password into a scrambling key.**
It runs your master password through a one-way process that always produces the same key from the same password. It's deliberately slow — about a tenth of a second — so anyone trying to guess millions of passwords is slowed to a crawl.

**3. The key is never saved anywhere.**
This is the important part. The key exists only while the program is running. Close it, and the key is gone. Next time you log in, your master password recreates the same key.

**4. Your passwords get scrambled with that key.**
When you save a password, the program scrambles it and writes the scrambled version to a file called `vault.json`. Opening that file shows you nothing but gibberish.

**5. Logging in checks your password without storing it.**
The program keeps a small fingerprint that can confirm your master password is right, but can't be worked backwards to reveal it or to unscramble anything.

**6. Unlocking reverses the scrambling.**
Type your master password, the program rebuilds the key, and your saved passwords become readable again — one at a time, only when you ask for one.

### What this means for you

- **Nobody can read your saved passwords without your master password.** Not someone who copies `vault.json`, not someone who steals your laptop.
- **If you forget your master password, your saved passwords are gone.** There's no reset link and no back door. That's the trade-off for the point above.
- **The web version locks itself after 15 minutes** of you not touching it, and forgets the key when you log out.

---

## Getting started

You need Python 3.10 or newer.

```bash
git clone https://github.com/ramezian1/Python-Password-Manager.git
cd Python-Password-Manager
pip install -r requirements.txt
```

### Run it in your browser

```bash
python app.py
```

It prints an address — open **http://127.0.0.1:5000** in your browser. Leave the terminal window open while you use it; closing it shuts the program down.

That address only works on your own computer. Other people on your wifi cannot reach it.

### Run it in the terminal

```bash
python main.py
```

No setup, no configuration files, no accounts. Either command just works after the install step above.

---

## Using the web version

1. **First visit** — it asks you to create a master password. Type it twice.
2. **Log in** — type that master password.
3. **Your vault** — a table of everything you've saved. Only the site names and usernames are shown; passwords stay hidden.
4. **Add an entry** — click *+ Add Entry*, fill in the site, your username, and a password. Or click *Generate* and it invents a strong one for you.
5. **Copy a password** — click *Copy* next to any row. It goes straight to your clipboard without ever appearing on screen.
6. **Change one** — click *Edit* to replace a password.
7. **Remove one** — click *Delete*. It asks you to confirm first.
8. **Log out** — click *Logout*, and the vault locks immediately.

## Using the terminal version

You get a numbered menu:

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

Type a number and press Enter. When it asks for a password, what you type stays invisible — that's on purpose.

Option **6** changes your master password. It unscrambles everything with the old one and re-scrambles it with the new one, so nothing is lost.

---

## Your vault is yours alone

Downloading this project does **not** give you someone else's passwords, and it doesn't come with a starter vault. There's nothing to log into on a fresh copy.

The file holding the passwords, `vault.json`, is created on your computer the first time you run the program, and it never leaves. It's listed in `.gitignore`, so even if you upload your own copy of this project to GitHub, that file stays behind.

So the sequence for a new copy is:

1. You run it.
2. It sees no vault and asks you to invent a master password.
3. From then on, that's the password that opens *your* vault.

If you ever want to start over, delete `vault.json` and run the program again.

---

## Important: earlier versions were not safe

Versions before this one saved the scrambling key to a file called `secret.key` — **and that file was uploaded to this public repository.** Anyone who downloaded the project could read every saved password.

That's fixed. The key is now built from your master password and never written down.

**If you used an older version, change every password you had stored in it, at the real website.** Re-scrambling them here doesn't help — they were already exposed. This is the one step the program can't do for you.

---

## Rules for a good password

When you save a password, the program checks that it has:

- at least 8 characters
- a lowercase letter
- an uppercase letter
- a number
- a symbol

Your master password has to pass these. For everything else it's a warning, not a refusal — it'll tell you the password is weak but still save it, because it's your call.

The *Generate* button always produces one that passes.

---

## What's in the folder

```
Python-Password-Manager/
├── app.py            The browser version
├── main.py           The terminal version, plus the shared scrambling logic
├── vault.json        Your saved passwords, scrambled (stays on your computer)
├── templates/        The web pages
├── static/           How the web pages look
├── requirements.txt  The extra packages needed
├── Procfile          Only used if you host it online
└── render.yaml       Only used if you host it online
```

`vault.json` is the only file that matters to you. Back it up if you like — it's useless to anyone without your master password. Losing it means losing your saved passwords.

---

## Putting it online (optional, and not really the point)

This is built to run on your own computer, which is the safer arrangement — your passwords never travel. The project does include the files needed to host it on [Render](https://render.com), left over from an earlier experiment, but think carefully before using them.

If you do host it:

1. Push your copy to GitHub.
2. On Render, choose **New → Web Service** and pick your repository.
3. Render reads `render.yaml` and fills in the settings itself.
4. Click **Create Web Service** and wait for it to build.
5. Open the address it gives you and set a master password on first visit.

Things that bite people:

- **Whoever visits first gets to set the master password.** A fresh copy has no vault, so the site will happily let the first stranger who finds it claim the account. If you host this, open it and set your password immediately.
- **Leave the worker count at 1.** The unlocking key is held in memory by a single running copy of the program. A second copy wouldn't know you'd logged in, and you'd get bounced back to the login page at random.
- **Free hosting goes to sleep** after 15 minutes with no visitors. Waking it takes about 30 seconds, and because the key lives in memory, you'll need to log in again.

Hosting needs one setting, `FLASK_SECRET_KEY`, which keeps your browser session valid. Render creates it automatically. Setting it is also how the program knows it's hosted rather than local, so it can tighten up how the browser handles the session. Running locally needs no settings at all.

---

## Honest limitations

- **Site names and usernames are readable** in `vault.json`. Only the passwords are scrambled. Someone with the file learns which accounts you have, but not how to get into them.
- **One person per vault.** There are no separate user accounts.
- **No limit on login attempts.** Someone with access to the running program can keep guessing, though the deliberately slow key process makes that painful.

## Ideas for later

- Scramble the site names and usernames too
- Limit repeated login attempts
- Export and import a backup
- Search your entries
- Two-factor authentication
