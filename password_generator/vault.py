"""Encrypted local credential vault.

Entries (site / username / password / timestamps) are kept in memory as
plain dataclasses, and only touch disk as a single Fernet-encrypted
blob. The encryption key is derived from a user-chosen master password
via PBKDF2-HMAC-SHA256, salted per-vault. There is no password-recovery
mechanism by design: forgetting the master password means the vault
cannot be decrypted, the same trade-off any local password manager makes.
"""

from __future__ import annotations

import base64
import csv
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

DEFAULT_ROTATION_DAYS = 30
SALT_SIZE = 16
KDF_ITERATIONS = 480_000

# Header candidates used when auto-detecting CSV columns exported from
# a spreadsheet with unknown/varying column names.
SITE_HEADER_HINTS = ["site", "website", "url", "service", "name", "account"]
USERNAME_HEADER_HINTS = ["username", "user", "email", "login", "user name"]
PASSWORD_HEADER_HINTS = ["password", "pass", "pwd"]


class VaultError(Exception):
    pass


class VaultLockedError(VaultError):
    pass


class InvalidMasterPasswordError(VaultError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class VaultEntry:
    id: str
    site: str
    username: str
    password: str
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def age_days(self) -> float:
        updated = datetime.fromisoformat(self.updated_at)
        return (datetime.now(timezone.utc) - updated).total_seconds() / 86400

    def rotation_due(self, rotation_days: int = DEFAULT_ROTATION_DAYS) -> bool:
        return self.age_days() >= rotation_days


def _derive_key(master_password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode("utf-8")))


def default_vault_path() -> Path:
    base = os.getenv("APPDATA") or str(Path.home())
    directory = Path(base) / "SecurePasswordGenerator"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "vault.dat"


class Vault:
    def __init__(self, path: Path, salt: bytes, key: bytes):
        self.path = path
        self._salt = salt
        self._key = key
        self._fernet = Fernet(key)
        self.entries: list[VaultEntry] = []

    # ---------- lifecycle ----------

    @classmethod
    def create(cls, path: Path, master_password: str) -> "Vault":
        if path.exists():
            raise VaultError(f"A vault already exists at {path}.")
        salt = os.urandom(SALT_SIZE)
        key = _derive_key(master_password, salt)
        vault = cls(path, salt, key)
        vault.save()
        return vault

    @classmethod
    def unlock(cls, path: Path, master_password: str) -> "Vault":
        if not path.exists():
            raise VaultError(f"No vault found at {path}.")
        raw = path.read_bytes()
        salt, token = raw[:SALT_SIZE], raw[SALT_SIZE:]
        key = _derive_key(master_password, salt)
        fernet = Fernet(key)
        try:
            plaintext = fernet.decrypt(token)
        except InvalidToken as exc:
            raise InvalidMasterPasswordError("Incorrect master password.") from exc

        vault = cls(path, salt, key)
        payload = json.loads(plaintext.decode("utf-8"))
        vault.entries = [VaultEntry(**entry) for entry in payload.get("entries", [])]
        return vault

    def save(self) -> None:
        payload = json.dumps({"entries": [asdict(e) for e in self.entries]}).encode("utf-8")
        token = self._fernet.encrypt(payload)
        self.path.write_bytes(self._salt + token)

    # ---------- entry management ----------

    def add_entry(self, site: str, username: str, password: str) -> VaultEntry:
        entry = VaultEntry(id=os.urandom(8).hex(), site=site, username=username, password=password)
        self.entries.append(entry)
        return entry

    def update_password(self, entry_id: str, new_password: str) -> VaultEntry:
        entry = self.get_entry(entry_id)
        entry.password = new_password
        entry.updated_at = _now_iso()
        return entry

    def delete_entry(self, entry_id: str) -> None:
        self.entries = [e for e in self.entries if e.id != entry_id]

    def get_entry(self, entry_id: str) -> VaultEntry:
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        raise VaultError(f"No entry with id {entry_id}.")

    def entries_due_for_rotation(self, rotation_days: int = DEFAULT_ROTATION_DAYS) -> list[VaultEntry]:
        return [e for e in self.entries if e.rotation_due(rotation_days)]

    # ---------- import ----------

    def import_csv(self, csv_path: Path, column_map: dict[str, str]) -> int:
        """Import rows from a CSV file (e.g. exported from Google Sheets).

        column_map maps logical fields ("site", "username", "password")
        to the actual CSV header names to read from.
        """
        added = 0
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                site = row.get(column_map.get("site", ""), "").strip()
                username = row.get(column_map.get("username", ""), "").strip()
                password = row.get(column_map.get("password", ""), "").strip()
                if not (site or username or password):
                    continue
                self.add_entry(site=site, username=username, password=password)
                added += 1
        return added


def detect_csv_columns(csv_path: Path) -> tuple[list[str], dict[str, Optional[str]]]:
    """Read just the header row and guess which column is which field."""
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader, [])

    def guess(hints: list[str]) -> Optional[str]:
        for header in headers:
            if header.strip().lower() in hints:
                return header
        return None

    guessed = {
        "site": guess(SITE_HEADER_HINTS),
        "username": guess(USERNAME_HEADER_HINTS),
        "password": guess(PASSWORD_HEADER_HINTS),
    }
    return headers, guessed
