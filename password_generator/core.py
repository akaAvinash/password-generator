"""Cryptographically secure password generation.

Uses `secrets` (not `random`) for every character choice, so output is
suitable for real credentials rather than simulations or games.
"""

from __future__ import annotations

import math
import secrets
import string
from dataclasses import dataclass

# Characters that are easy to misread or mistype (capital O vs zero,
# capital I vs lowercase l vs one, pipe vs I/l).
AMBIGUOUS_CHARS = "O0Il1|"

ENTROPY_PRESETS = {
    "128-bit": 128,
    "256-bit": 256,
    "512-bit": 512,
    "1024-bit": 1024,
}


class PasswordGeneratorError(ValueError):
    """Raised when the requested options can't produce a valid password."""


@dataclass
class CharsetOptions:
    use_lowercase: bool = True
    use_uppercase: bool = True
    use_digits: bool = True
    use_symbols: bool = True
    avoid_ambiguous: bool = True

    def build(self) -> dict[str, str]:
        """Return the selected character groups, keyed by name."""
        groups: dict[str, str] = {}
        if self.use_lowercase:
            groups["lowercase"] = string.ascii_lowercase
        if self.use_uppercase:
            groups["uppercase"] = string.ascii_uppercase
        if self.use_digits:
            groups["digits"] = string.digits
        if self.use_symbols:
            groups["symbols"] = string.punctuation

        if self.avoid_ambiguous:
            groups = {
                name: "".join(c for c in chars if c not in AMBIGUOUS_CHARS)
                for name, chars in groups.items()
            }
            # Drop any group emptied entirely by ambiguous-char filtering.
            groups = {name: chars for name, chars in groups.items() if chars}

        return groups


def calculate_entropy(length: int, charset_size: int) -> float:
    """Shannon entropy in bits for a random string of `length` drawn
    uniformly from an alphabet of `charset_size` symbols."""
    if charset_size <= 1 or length <= 0:
        return 0.0
    return length * math.log2(charset_size)


def required_length_for_entropy(target_bits: float, charset_size: int) -> int:
    """Smallest length whose max entropy meets or exceeds target_bits."""
    if charset_size <= 1:
        raise PasswordGeneratorError("Character set must contain at least 2 distinct characters.")
    return max(1, math.ceil(target_bits / math.log2(charset_size)))


def strength_label(entropy_bits: float) -> str:
    if entropy_bits < 50:
        return "Weak"
    if entropy_bits < 80:
        return "Medium"
    if entropy_bits < 128:
        return "Strong"
    if entropy_bits < 256:
        return "Very Strong"
    return "Excellent"


def generate_password(charset_groups: dict[str, str], length: int) -> str:
    """Generate one password of the given length, guaranteeing at least
    one character from every selected group."""
    if not charset_groups:
        raise PasswordGeneratorError("Select at least one character type.")

    all_chars = "".join(charset_groups.values())
    if not all_chars:
        raise PasswordGeneratorError("Selected character types produced an empty character set.")

    if length < len(charset_groups):
        raise PasswordGeneratorError(
            f"Length must be at least {len(charset_groups)} to include every selected character type."
        )

    password_chars = [secrets.choice(chars) for chars in charset_groups.values()]
    password_chars += [secrets.choice(all_chars) for _ in range(length - len(password_chars))]

    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def generate_for_entropy_target(options: CharsetOptions, target_bits: float):
    """Generate a password whose length is auto-sized to guarantee at
    least `target_bits` of entropy, regardless of which character
    groups are selected.

    Returns (password, length, charset_size, actual_entropy_bits).
    """
    groups = options.build()
    if not groups:
        raise PasswordGeneratorError("Select at least one character type.")

    charset_size = len(set("".join(groups.values())))
    length = required_length_for_entropy(target_bits, charset_size)
    password = generate_password(groups, length)
    actual_entropy = calculate_entropy(length, charset_size)
    return password, length, charset_size, actual_entropy


def generate_fixed_length(options: CharsetOptions, length: int):
    """Generate a password of an exact, user-chosen length.

    Returns (password, charset_size, actual_entropy_bits).
    """
    groups = options.build()
    if not groups:
        raise PasswordGeneratorError("Select at least one character type.")

    charset_size = len(set("".join(groups.values())))
    password = generate_password(groups, length)
    actual_entropy = calculate_entropy(length, charset_size)
    return password, charset_size, actual_entropy
