# Building the Windows installer

Two steps: freeze the app with PyInstaller, then wrap it with Inno Setup.

## 1. Freeze with PyInstaller

```bash
pip install -r requirements-dev.txt
python build_tools/make_icon.py          # only needed if assets/icon.ico is missing
pyinstaller build_tools/password_generator.spec --noconfirm
```

Produces `dist/SecurePasswordGenerator.exe` (a windowed, single-file exe —
no console, no external Python required to run it).

## 2. Build the installer with Inno Setup

Requires [Inno Setup 6](https://jrsoftware.org/isinfo.php).

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build_tools/installer.iss
```

Produces `Output/SecurePasswordGenerator-Setup-<version>.exe` — a
per-user installer (no admin rights needed) with a Start Menu entry,
optional desktop shortcut, and a proper uninstaller registered in
"Apps & Features".

Both `dist/`, `build/`, and `Output/` are git-ignored — only the specs
that produce them are tracked.
