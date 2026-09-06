# Secure Password Generator

A desktop password generator with a modern GUI (CustomTkinter) that
generates cryptographically secure passwords targeting up to **512 bits
of entropy**.

## Features

- Uses Python's `secrets` module (CSPRNG) for every character choice —
  never `random`.
- Entropy-target mode: pick 128 / 256 / 512 / 1024-bit, and the password
  length is automatically computed so the result always meets or
  exceeds that target, no matter which character types you enable.
- Toggle lowercase / uppercase / digits / symbols, and optionally
  exclude visually ambiguous characters (`O`, `0`, `I`, `l`, `1`, `|`).
- Generate multiple passwords at once, each with its length, character
  set size, and strength shown.
- One-click copy to clipboard.
- Light/dark theme.

### Encrypted credential vault

A second tab manages your *existing* passwords for real sites:

- **Import from CSV** — export your Google Sheet as CSV (File > Download
  > CSV) and import it; columns are auto-detected (site/username/password)
  with a mapping screen if names don't match.
- **Encrypted at rest** — entries are stored in `%APPDATA%\SecurePasswordGenerator\vault.dat`,
  encrypted with a key derived from a master password you set (PBKDF2-HMAC-SHA256
  + Fernet/AES). There is no password recovery — forgetting the master
  password means the vault cannot be opened, the same trade-off any
  local password manager makes.
- **Rotation reminders** — entries older than 30 days are flagged
  "Rotation due". Clicking **Rotate** generates a new password and saves
  it to the vault immediately; you still need to change it on the real
  website yourself — the app has no way to log into arbitrary sites and
  change your password there automatically.

## Running from source

```bash
pip install -r requirements.txt
python main.py
```

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Building a Windows installer

See [build_tools/README.md](build_tools/README.md).
