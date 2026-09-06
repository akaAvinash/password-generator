import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from password_generator.vault import (
    InvalidMasterPasswordError,
    Vault,
    VaultError,
    detect_csv_columns,
)


@pytest.fixture
def vault_path(tmp_path):
    return tmp_path / "vault.dat"


def test_create_and_unlock_roundtrip(vault_path):
    vault = Vault.create(vault_path, "correct horse battery staple")
    vault.add_entry("github.com", "alice", "s3cr3t!")
    vault.save()

    reopened = Vault.unlock(vault_path, "correct horse battery staple")
    assert len(reopened.entries) == 1
    assert reopened.entries[0].site == "github.com"
    assert reopened.entries[0].password == "s3cr3t!"


def test_unlock_wrong_password_raises(vault_path):
    Vault.create(vault_path, "correct password")
    with pytest.raises(InvalidMasterPasswordError):
        Vault.unlock(vault_path, "wrong password")


def test_create_twice_raises(vault_path):
    Vault.create(vault_path, "pw")
    with pytest.raises(VaultError):
        Vault.create(vault_path, "pw")


def test_vault_file_does_not_contain_plaintext_secrets(vault_path):
    vault = Vault.create(vault_path, "master-pw")
    vault.add_entry("bank.example.com", "bob", "hunter2-super-secret")
    vault.save()

    raw = vault_path.read_bytes()
    assert b"hunter2-super-secret" not in raw
    assert b"bank.example.com" not in raw
    assert b"bob" not in raw


def test_update_password_bumps_updated_at(vault_path):
    vault = Vault.create(vault_path, "pw")
    entry = vault.add_entry("site.com", "user", "old-pass")
    old_updated = entry.updated_at

    vault.update_password(entry.id, "new-pass")
    assert entry.password == "new-pass"
    assert entry.updated_at >= old_updated


def test_delete_entry_removes_it(vault_path):
    vault = Vault.create(vault_path, "pw")
    entry = vault.add_entry("site.com", "user", "pass")
    vault.delete_entry(entry.id)
    assert vault.entries == []


def test_get_entry_missing_raises(vault_path):
    vault = Vault.create(vault_path, "pw")
    with pytest.raises(VaultError):
        vault.get_entry("does-not-exist")


def test_entries_due_for_rotation(vault_path):
    vault = Vault.create(vault_path, "pw")
    fresh = vault.add_entry("fresh.com", "u", "p")
    stale = vault.add_entry("stale.com", "u", "p")
    stale.updated_at = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()

    due = vault.entries_due_for_rotation(rotation_days=30)
    assert due == [stale]
    assert fresh not in due


def test_import_csv_with_explicit_column_map(tmp_path, vault_path):
    csv_path = tmp_path / "passwords.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Service", "Login", "Secret"])
        writer.writerow(["github.com", "alice", "pw1"])
        writer.writerow(["gmail.com", "alice@gmail.com", "pw2"])

    vault = Vault.create(vault_path, "pw")
    added = vault.import_csv(
        csv_path, {"site": "Service", "username": "Login", "password": "Secret"}
    )

    assert added == 2
    assert {e.site for e in vault.entries} == {"github.com", "gmail.com"}


def test_import_csv_skips_fully_blank_rows(tmp_path, vault_path):
    csv_path = tmp_path / "passwords.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["site", "username", "password"])
        writer.writerow(["", "", ""])
        writer.writerow(["a.com", "u", "p"])

    vault = Vault.create(vault_path, "pw")
    added = vault.import_csv(csv_path, {"site": "site", "username": "username", "password": "password"})
    assert added == 1


def test_detect_csv_columns_guesses_common_headers(tmp_path):
    csv_path = tmp_path / "sheet.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Website", "Email", "Password"])
        writer.writerow(["x.com", "me@x.com", "pw"])

    headers, guessed = detect_csv_columns(csv_path)
    assert headers == ["Website", "Email", "Password"]
    assert guessed["site"] == "Website"
    assert guessed["username"] == "Email"
    assert guessed["password"] == "Password"


def test_detect_csv_columns_unmatched_returns_none(tmp_path):
    csv_path = tmp_path / "sheet.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Col A", "Col B", "Col C"])
        writer.writerow(["1", "2", "3"])

    _, guessed = detect_csv_columns(csv_path)
    assert guessed == {"site": None, "username": None, "password": None}
