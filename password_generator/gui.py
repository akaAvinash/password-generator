"""CustomTkinter desktop UI for the password generator."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from .core import (
    CharsetOptions,
    ENTROPY_PRESETS,
    PasswordGeneratorError,
    generate_for_entropy_target,
    strength_label,
)

APP_TITLE = "Secure Password Generator"
WINDOW_SIZE = "760x640"

STRENGTH_COLORS = {
    "Weak": "#e5484d",
    "Medium": "#f5a623",
    "Strong": "#3dd68c",
    "Very Strong": "#2fb8e0",
    "Excellent": "#7c5cff",
}


class PasswordRow(ctk.CTkFrame):
    """One generated password: text field + strength badge + copy button."""

    def __init__(self, master, password: str, length: int, charset_size: int, entropy: float, on_copy):
        super().__init__(master, corner_radius=10, fg_color=("gray92", "gray17"))
        self.password = password
        self.on_copy = on_copy

        self.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(
            self,
            font=ctk.CTkFont(family="Consolas", size=14),
            show="",
        )
        self.entry.insert(0, password)
        self.entry.configure(state="readonly")
        self.entry.grid(row=0, column=0, sticky="ew", padx=(12, 8), pady=(12, 4))

        self.copy_btn = ctk.CTkButton(
            self, text="Copy", width=70, command=self._copy
        )
        self.copy_btn.grid(row=0, column=1, padx=(0, 12), pady=(12, 4))

        strength = strength_label(entropy)
        info_text = f"Length {length}  |  Charset {charset_size}  |  Entropy {entropy:.1f} bits  |  {strength}"
        info_label = ctk.CTkLabel(
            self,
            text=info_text,
            font=ctk.CTkFont(size=11),
            text_color=STRENGTH_COLORS.get(strength, "gray"),
            anchor="w",
        )
        info_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10))

    def _copy(self):
        self.on_copy(self.password)
        original = self.copy_btn.cget("text")
        self.copy_btn.configure(text="Copied!")
        self.after(1200, lambda: self.copy_btn.configure(text=original))


class PasswordGeneratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(640, 560)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_options()
        self._build_results_area()
        self._build_status_bar()

        self.result_rows: list[PasswordRow] = []

    # ---------- UI construction ----------

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header, text="🔐 Secure Password Generator",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ctk.CTkLabel(
            header,
            text="Cryptographically secure passwords, sized to hit your entropy target.",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        subtitle.grid(row=1, column=0, sticky="w")

        self.theme_switch = ctk.CTkSegmentedButton(
            header, values=["Dark", "Light"], command=self._on_theme_change
        )
        self.theme_switch.set("Dark")
        self.theme_switch.grid(row=0, column=1, rowspan=2, sticky="e")

    def _build_options(self):
        panel = ctk.CTkFrame(self, corner_radius=12)
        panel.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        for col in range(4):
            panel.grid_columnconfigure(col, weight=1)

        # Entropy target
        entropy_label = ctk.CTkLabel(panel, text="Entropy target", font=ctk.CTkFont(weight="bold"))
        entropy_label.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))

        self.entropy_var = tk.StringVar(value="512-bit")
        self.entropy_menu = ctk.CTkOptionMenu(
            panel, values=list(ENTROPY_PRESETS.keys()), variable=self.entropy_var
        )
        self.entropy_menu.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))

        # Count
        count_label = ctk.CTkLabel(panel, text="How many passwords", font=ctk.CTkFont(weight="bold"))
        count_label.grid(row=0, column=1, sticky="w", padx=16, pady=(16, 4))

        self.count_var = tk.StringVar(value="1")
        self.count_menu = ctk.CTkOptionMenu(
            panel, values=[str(n) for n in (1, 3, 5, 10, 20)], variable=self.count_var
        )
        self.count_menu.grid(row=1, column=1, sticky="ew", padx=16, pady=(0, 12))

        # Character type checkboxes
        types_label = ctk.CTkLabel(panel, text="Character types", font=ctk.CTkFont(weight="bold"))
        types_label.grid(row=2, column=0, sticky="w", padx=16, pady=(4, 4))

        self.lower_var = tk.BooleanVar(value=True)
        self.upper_var = tk.BooleanVar(value=True)
        self.digits_var = tk.BooleanVar(value=True)
        self.symbols_var = tk.BooleanVar(value=True)
        self.avoid_ambiguous_var = tk.BooleanVar(value=True)

        checks = [
            ("Lowercase (a-z)", self.lower_var),
            ("Uppercase (A-Z)", self.upper_var),
            ("Digits (0-9)", self.digits_var),
            ("Symbols (!@#...)", self.symbols_var),
        ]
        for i, (text, var) in enumerate(checks):
            cb = ctk.CTkCheckBox(panel, text=text, variable=var)
            cb.grid(row=3 + i // 2, column=(i % 2), sticky="w", padx=16, pady=4)

        ambiguous_cb = ctk.CTkCheckBox(
            panel, text="Avoid ambiguous characters (O, 0, I, l, 1, |)",
            variable=self.avoid_ambiguous_var,
        )
        ambiguous_cb.grid(row=5, column=0, columnspan=2, sticky="w", padx=16, pady=(4, 16))

        # Generate button
        self.generate_btn = ctk.CTkButton(
            panel, text="Generate", font=ctk.CTkFont(size=15, weight="bold"),
            height=44, command=self.on_generate,
        )
        self.generate_btn.grid(row=2, column=2, rowspan=4, columnspan=2, sticky="nsew", padx=16, pady=16)

    def _build_results_area(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 10))
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self.results_scroll = ctk.CTkScrollableFrame(container, label_text="Generated passwords")
        self.results_scroll.grid(row=0, column=0, sticky="nsew")
        self.results_scroll.grid_columnconfigure(0, weight=1)

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Ready.")
        status = ctk.CTkLabel(
            self, textvariable=self.status_var, font=ctk.CTkFont(size=11),
            text_color="gray60", anchor="w",
        )
        status.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 10))

    # ---------- Behavior ----------

    def _on_theme_change(self, value: str):
        ctk.set_appearance_mode(value.lower())

    def _clear_results(self):
        for row in self.result_rows:
            row.destroy()
        self.result_rows.clear()

    def on_generate(self):
        options = CharsetOptions(
            use_lowercase=self.lower_var.get(),
            use_uppercase=self.upper_var.get(),
            use_digits=self.digits_var.get(),
            use_symbols=self.symbols_var.get(),
            avoid_ambiguous=self.avoid_ambiguous_var.get(),
        )
        target_bits = ENTROPY_PRESETS[self.entropy_var.get()]
        count = int(self.count_var.get())

        try:
            self._clear_results()
            for _ in range(count):
                password, length, charset_size, entropy = generate_for_entropy_target(options, target_bits)
                row = PasswordRow(
                    self.results_scroll, password, length, charset_size, entropy,
                    on_copy=self.copy_to_clipboard,
                )
                row.grid(sticky="ew", pady=6, padx=2)
                self.result_rows.append(row)

            self.status_var.set(
                f"Generated {count} password(s) targeting {self.entropy_var.get()} entropy."
            )
        except PasswordGeneratorError as exc:
            messagebox.showerror("Cannot generate password", str(exc))
            self.status_var.set("Generation failed — see error dialog.")

    def copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()  # ensures clipboard content persists after app focus changes
        self.status_var.set("Password copied to clipboard.")


def run():
    app = PasswordGeneratorApp()
    app.mainloop()


if __name__ == "__main__":
    run()
