"""CustomTkinter UI for the encrypted credential vault: unlock/create
screen, entry list with rotation badges, add/import/rotate flows."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .core import CharsetOptions, generate_fixed_length
from .vault import (
    DEFAULT_ROTATION_DAYS,
    InvalidMasterPasswordError,
    Vault,
    VaultError,
    default_vault_path,
    detect_csv_columns,
)

ROTATION_PASSWORD_LENGTH = 24
NONE_COLUMN = "-- none --"


def _generate_strong_password() -> str:
    password, _charset_size, _entropy = generate_fixed_length(CharsetOptions(), ROTATION_PASSWORD_LENGTH)
    return password


class MasterPasswordDialog(ctk.CTkToplevel):
    """Modal used for both 'create vault' and 'unlock vault' flows."""

    def __init__(self, master, mode: str, on_submit):
        super().__init__(master)
        self.title("Create vault" if mode == "create" else "Unlock vault")
        self.geometry("360x260" if mode == "create" else "360x190")
        self.resizable(False, False)
        self.on_submit = on_submit
        self.mode = mode
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        label_text = (
            "Choose a master password for your new vault.\nThere is no recovery — if you forget it, the vault cannot be opened."
            if mode == "create"
            else "Enter your master password to unlock the vault."
        )
        ctk.CTkLabel(self, text=label_text, justify="left", wraplength=320).grid(
            row=0, column=0, padx=20, pady=(20, 10), sticky="w"
        )

        self.password_entry = ctk.CTkEntry(self, placeholder_text="Master password", show="•", width=300)
        self.password_entry.grid(row=1, column=0, padx=20, pady=6)
        self.password_entry.focus()

        if mode == "create":
            self.confirm_entry = ctk.CTkEntry(self, placeholder_text="Confirm password", show="•", width=300)
            self.confirm_entry.grid(row=2, column=0, padx=20, pady=6)
        else:
            self.confirm_entry = None

        self.error_label = ctk.CTkLabel(self, text="", text_color="#e5484d")
        self.error_label.grid(row=3, column=0, padx=20, pady=(4, 0))

        submit_text = "Create vault" if mode == "create" else "Unlock"
        submit_btn = ctk.CTkButton(self, text=submit_text, command=self._submit)
        submit_btn.grid(row=4, column=0, padx=20, pady=16)

        self.bind("<Return>", lambda _event: self._submit())

    def _submit(self):
        password = self.password_entry.get()
        if not password:
            self.error_label.configure(text="Password cannot be empty.")
            return
        if self.mode == "create":
            if len(password) < 8:
                self.error_label.configure(text="Use at least 8 characters.")
                return
            if password != self.confirm_entry.get():
                self.error_label.configure(text="Passwords do not match.")
                return

        try:
            self.on_submit(password)
            self.destroy()
        except InvalidMasterPasswordError:
            self.error_label.configure(text="Incorrect master password.")
        except VaultError as exc:
            self.error_label.configure(text=str(exc))


class AddEntryDialog(ctk.CTkToplevel):
    def __init__(self, master, on_submit):
        super().__init__(master)
        self.title("Add credential")
        self.geometry("380x300")
        self.resizable(False, False)
        self.on_submit = on_submit
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        self.site_entry = ctk.CTkEntry(self, placeholder_text="Site / service (e.g. github.com)", width=320)
        self.site_entry.grid(row=0, column=0, padx=20, pady=(20, 6))

        self.username_entry = ctk.CTkEntry(self, placeholder_text="Username / email", width=320)
        self.username_entry.grid(row=1, column=0, padx=20, pady=6)

        pw_row = ctk.CTkFrame(self, fg_color="transparent")
        pw_row.grid(row=2, column=0, padx=20, pady=6, sticky="ew")
        pw_row.grid_columnconfigure(0, weight=1)

        self.password_entry = ctk.CTkEntry(pw_row, placeholder_text="Password", show="•")
        self.password_entry.grid(row=0, column=0, sticky="ew")

        generate_btn = ctk.CTkButton(pw_row, text="Generate", width=90, command=self._fill_generated)
        generate_btn.grid(row=0, column=1, padx=(8, 0))

        self.error_label = ctk.CTkLabel(self, text="", text_color="#e5484d")
        self.error_label.grid(row=3, column=0, padx=20, pady=(4, 0))

        save_btn = ctk.CTkButton(self, text="Save to vault", command=self._submit)
        save_btn.grid(row=4, column=0, padx=20, pady=20)

    def _fill_generated(self):
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, _generate_strong_password())
        self.password_entry.configure(show="")

    def _submit(self):
        site = self.site_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not site or not password:
            self.error_label.configure(text="Site and password are required.")
            return
        self.on_submit(site, username, password)
        self.destroy()


class ImportMappingDialog(ctk.CTkToplevel):
    def __init__(self, master, csv_path: Path, on_submit):
        super().__init__(master)
        self.title("Import from CSV")
        self.geometry("420x340")
        self.resizable(False, False)
        self.on_submit = on_submit
        self.csv_path = csv_path
        self.grab_set()

        headers, guessed = detect_csv_columns(csv_path)
        options = [NONE_COLUMN] + headers

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text=f"Map columns from {csv_path.name}:",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.site_var = tk.StringVar(value=guessed["site"] or NONE_COLUMN)
        self.username_var = tk.StringVar(value=guessed["username"] or NONE_COLUMN)
        self.password_var = tk.StringVar(value=guessed["password"] or NONE_COLUMN)

        for i, (label, var) in enumerate([
            ("Site / service column", self.site_var),
            ("Username column", self.username_var),
            ("Password column", self.password_var),
        ]):
            ctk.CTkLabel(self, text=label).grid(row=1 + 2 * i, column=0, padx=20, sticky="w")
            ctk.CTkOptionMenu(self, values=options, variable=var).grid(
                row=2 + 2 * i, column=0, padx=20, pady=(0, 8), sticky="ew"
            )

        self.error_label = ctk.CTkLabel(self, text="", text_color="#e5484d")
        self.error_label.grid(row=7, column=0, padx=20, pady=(4, 0))

        import_btn = ctk.CTkButton(self, text="Import", command=self._submit)
        import_btn.grid(row=8, column=0, padx=20, pady=16)

    def _submit(self):
        if self.password_var.get() == NONE_COLUMN:
            self.error_label.configure(text="You must select a password column.")
            return

        column_map = {}
        if self.site_var.get() != NONE_COLUMN:
            column_map["site"] = self.site_var.get()
        if self.username_var.get() != NONE_COLUMN:
            column_map["username"] = self.username_var.get()
        column_map["password"] = self.password_var.get()

        self.on_submit(self.csv_path, column_map)
        self.destroy()


class RotatedPasswordDialog(ctk.CTkToplevel):
    """Shown after a rotation: the vault is already updated, but the
    real website still has the old password until the user changes it."""

    def __init__(self, master, site: str, new_password: str, on_copy):
        super().__init__(master)
        self.title("Password rotated")
        self.geometry("420x220")
        self.resizable(False, False)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text=f"New password generated for {site}.\nUpdate it on the actual website, then it's done — "
                 f"the vault already has this value.",
            justify="left", wraplength=380,
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        entry = ctk.CTkEntry(row, font=ctk.CTkFont(family="Consolas", size=13))
        entry.insert(0, new_password)
        entry.configure(state="readonly")
        entry.grid(row=0, column=0, sticky="ew")

        copy_btn = ctk.CTkButton(row, text="Copy", width=70, command=lambda: on_copy(new_password))
        copy_btn.grid(row=0, column=1, padx=(8, 0))

        ctk.CTkButton(self, text="Done", command=self.destroy).grid(row=2, column=0, pady=10)


class VaultEntryRow(ctk.CTkFrame):
    def __init__(self, master, entry, on_copy, on_rotate, on_delete):
        super().__init__(master, corner_radius=10, fg_color=("gray92", "gray17"))
        self.entry = entry
        self.on_copy = on_copy

        self.grid_columnconfigure(1, weight=1)

        site_label = ctk.CTkLabel(
            self, text=entry.site or "(no site name)", font=ctk.CTkFont(weight="bold"), anchor="w"
        )
        site_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 0))

        user_label = ctk.CTkLabel(self, text=entry.username or "(no username)", text_color="gray60", anchor="w")
        user_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=12)

        self.password_entry = ctk.CTkEntry(self, font=ctk.CTkFont(family="Consolas", size=13), show="•")
        self.password_entry.insert(0, entry.password)
        self.password_entry.configure(state="readonly")
        self.password_entry.grid(row=2, column=0, sticky="ew", padx=(12, 6), pady=8)

        self._revealed = False
        self.reveal_btn = ctk.CTkButton(self, text="Show", width=60, command=self._toggle_reveal)
        self.reveal_btn.grid(row=2, column=1, padx=4, pady=8)

        copy_btn = ctk.CTkButton(self, text="Copy", width=60, command=lambda: on_copy(entry.password))
        copy_btn.grid(row=2, column=2, padx=4, pady=8)

        rotate_btn = ctk.CTkButton(self, text="Rotate", width=70, command=lambda: on_rotate(entry.id))
        rotate_btn.grid(row=2, column=3, padx=4, pady=8)

        delete_btn = ctk.CTkButton(
            self, text="Delete", width=70, fg_color="#8a2f36", hover_color="#6e252a",
            command=lambda: on_delete(entry.id),
        )
        delete_btn.grid(row=2, column=4, padx=(4, 12), pady=8)

        age = entry.age_days()
        due = entry.rotation_due(DEFAULT_ROTATION_DAYS)
        status_text = (
            f"Rotation due — last changed {age:.0f} days ago"
            if due
            else f"Last changed {age:.0f} days ago"
        )
        status_label = ctk.CTkLabel(
            self, text=status_text,
            text_color="#f5a623" if due else "gray60",
            font=ctk.CTkFont(size=11), anchor="w",
        )
        status_label.grid(row=3, column=0, columnspan=5, sticky="w", padx=12, pady=(0, 10))

    def _toggle_reveal(self):
        self._revealed = not self._revealed
        self.password_entry.configure(show="" if self._revealed else "•")
        self.reveal_btn.configure(text="Hide" if self._revealed else "Show")


class VaultTab(ctk.CTkFrame):
    def __init__(self, master, on_copy, on_status):
        super().__init__(master, fg_color="transparent")
        self.on_copy = on_copy
        self.on_status = on_status
        self.vault: Vault | None = None
        self.vault_path = default_vault_path()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._show_locked_view()

    # ---------- locked / unlock screens ----------

    def _clear(self):
        for child in self.winfo_children():
            child.destroy()

    def _show_locked_view(self):
        self._clear()
        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.grid(row=0, column=0)

        vault_exists = self.vault_path.exists()
        title = "Unlock your vault" if vault_exists else "Create your vault"
        subtitle = (
            f"Vault file: {self.vault_path}"
            if vault_exists
            else "No vault found yet. Set a master password to create one."
        )

        ctk.CTkLabel(wrapper, text=title, font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(40, 4))
        ctk.CTkLabel(wrapper, text=subtitle, text_color="gray60", wraplength=420).pack(pady=(0, 20))

        action_text = "Unlock" if vault_exists else "Create vault"
        ctk.CTkButton(wrapper, text=action_text, width=200, command=self._open_master_password_dialog).pack()

    def _open_master_password_dialog(self):
        mode = "unlock" if self.vault_path.exists() else "create"
        MasterPasswordDialog(self, mode, on_submit=self._handle_master_password)

    def _handle_master_password(self, password: str):
        if self.vault_path.exists():
            self.vault = Vault.unlock(self.vault_path, password)
            self.on_status("Vault unlocked.")
        else:
            self.vault = Vault.create(self.vault_path, password)
            self.on_status("Vault created.")
        self._show_unlocked_view()

    # ---------- unlocked screen ----------

    def _show_unlocked_view(self):
        self._clear()
        self.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        due_count = len(self.vault.entries_due_for_rotation())
        due_text = f"  •  {due_count} due for rotation" if due_count else ""
        ctk.CTkLabel(
            toolbar, text=f"{len(self.vault.entries)} saved credential(s){due_text}",
            font=ctk.CTkFont(weight="bold"),
            text_color="#f5a623" if due_count else None,
        ).pack(side="left", padx=(4, 0))

        ctk.CTkButton(toolbar, text="Add Entry", width=100, command=self._open_add_dialog).pack(side="right", padx=4)
        ctk.CTkButton(toolbar, text="Import CSV", width=100, command=self._open_import_dialog).pack(side="right", padx=4)
        ctk.CTkButton(toolbar, text="Lock Vault", width=100, command=self._lock).pack(side="right", padx=4)

        self.entries_scroll = ctk.CTkScrollableFrame(self, label_text="Credentials")
        self.entries_scroll.grid(row=1, column=0, sticky="nsew")
        self.entries_scroll.grid_columnconfigure(0, weight=1)

        self._refresh_entries()

    def _refresh_entries(self):
        for child in self.entries_scroll.winfo_children():
            child.destroy()
        for entry in self.vault.entries:
            row = VaultEntryRow(
                self.entries_scroll, entry,
                on_copy=self.on_copy, on_rotate=self._rotate_entry, on_delete=self._delete_entry,
            )
            row.grid(sticky="ew", padx=2, pady=6)

    def _lock(self):
        self.vault.save()
        self.vault = None
        self.on_status("Vault locked.")
        self._show_locked_view()

    def _open_add_dialog(self):
        AddEntryDialog(self, on_submit=self._add_entry)

    def _add_entry(self, site: str, username: str, password: str):
        self.vault.add_entry(site, username, password)
        self.vault.save()
        self._show_unlocked_view()
        self.on_status(f"Added credential for {site}.")

    def _open_import_dialog(self):
        path_str = filedialog.askopenfilename(
            title="Select CSV exported from Google Sheets",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path_str:
            return
        ImportMappingDialog(self, Path(path_str), on_submit=self._import_csv)

    def _import_csv(self, csv_path: Path, column_map: dict):
        try:
            added = self.vault.import_csv(csv_path, column_map)
            self.vault.save()
            self._show_unlocked_view()
            self.on_status(f"Imported {added} credential(s) from {csv_path.name}.")
        except Exception as exc:  # noqa: BLE001 - surfaced to the user, not swallowed
            messagebox.showerror("Import failed", str(exc))

    def _rotate_entry(self, entry_id: str):
        entry = self.vault.get_entry(entry_id)
        if not messagebox.askyesno(
            "Rotate password",
            f"Generate a new password for {entry.site or entry.username}?\n\n"
            "The vault will be updated immediately, but you still need to change the password on the real "
            "website afterward.",
        ):
            return
        new_password = _generate_strong_password()
        self.vault.update_password(entry_id, new_password)
        self.vault.save()
        self._refresh_entries()
        self.on_status(f"Rotated password for {entry.site or entry.username}.")
        RotatedPasswordDialog(self, entry.site or entry.username, new_password, on_copy=self.on_copy)

    def _delete_entry(self, entry_id: str):
        entry = self.vault.get_entry(entry_id)
        if not messagebox.askyesno("Delete credential", f"Delete the saved credential for {entry.site}?"):
            return
        self.vault.delete_entry(entry_id)
        self.vault.save()
        self._refresh_entries()
        self.on_status(f"Deleted credential for {entry.site}.")
