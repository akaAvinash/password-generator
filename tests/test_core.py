import math
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from password_generator.core import (
    AMBIGUOUS_CHARS,
    CharsetOptions,
    PasswordGeneratorError,
    calculate_entropy,
    generate_fixed_length,
    generate_for_entropy_target,
    generate_password,
    required_length_for_entropy,
    strength_label,
)


def test_calculate_entropy_basic():
    assert calculate_entropy(1, 2) == 1.0
    assert calculate_entropy(8, 256) == 64.0
    assert calculate_entropy(0, 100) == 0.0


def test_required_length_for_entropy_meets_target():
    charset_size = 94
    length = required_length_for_entropy(512, charset_size)
    achieved = calculate_entropy(length, charset_size)
    assert achieved >= 512
    # And one character less should fall short (tight bound).
    assert calculate_entropy(length - 1, charset_size) < 512


def test_required_length_rejects_trivial_charset():
    with pytest.raises(PasswordGeneratorError):
        required_length_for_entropy(128, 1)


def test_charset_options_build_all_enabled():
    options = CharsetOptions(avoid_ambiguous=False)
    groups = options.build()
    assert set(groups.keys()) == {"lowercase", "uppercase", "digits", "symbols"}
    assert groups["lowercase"] == string.ascii_lowercase
    assert groups["symbols"] == string.punctuation


def test_charset_options_avoid_ambiguous_strips_chars():
    options = CharsetOptions(
        use_lowercase=True, use_uppercase=True, use_digits=True, use_symbols=False,
        avoid_ambiguous=True,
    )
    groups = options.build()
    combined = "".join(groups.values())
    for ch in AMBIGUOUS_CHARS:
        assert ch not in combined


def test_charset_options_none_selected():
    options = CharsetOptions(
        use_lowercase=False, use_uppercase=False, use_digits=False, use_symbols=False
    )
    assert options.build() == {}


def test_generate_password_contains_each_group():
    groups = {"digits": "0123456789", "symbols": "!@#"}
    pwd = generate_password(groups, 10)
    assert len(pwd) == 10
    assert any(c in groups["digits"] for c in pwd)
    assert any(c in groups["symbols"] for c in pwd)


def test_generate_password_too_short_for_groups_raises():
    groups = {"a": "xy", "b": "12", "c": "!@"}
    with pytest.raises(PasswordGeneratorError):
        generate_password(groups, 2)


def test_generate_password_no_groups_raises():
    with pytest.raises(PasswordGeneratorError):
        generate_password({}, 10)


def test_generate_for_entropy_target_meets_or_exceeds_512():
    options = CharsetOptions()
    password, length, charset_size, entropy = generate_for_entropy_target(options, 512)
    assert len(password) == length
    assert entropy >= 512


def test_generate_for_entropy_target_scales_with_smaller_charset():
    # Fewer character types -> smaller charset -> longer password needed
    # to reach the same entropy target.
    rich = CharsetOptions(avoid_ambiguous=False)
    lean = CharsetOptions(
        use_lowercase=True, use_uppercase=False, use_digits=False, use_symbols=False,
        avoid_ambiguous=False,
    )
    _, len_rich, _, entropy_rich = generate_for_entropy_target(rich, 256)
    _, len_lean, _, entropy_lean = generate_for_entropy_target(lean, 256)
    assert entropy_rich >= 256
    assert entropy_lean >= 256
    assert len_lean > len_rich


def test_generate_fixed_length_respects_length():
    options = CharsetOptions()
    password, charset_size, entropy = generate_fixed_length(options, 40)
    assert len(password) == 40
    assert entropy == calculate_entropy(40, charset_size)


def test_strength_label_thresholds():
    assert strength_label(10) == "Weak"
    assert strength_label(60) == "Medium"
    assert strength_label(100) == "Strong"
    assert strength_label(200) == "Very Strong"
    assert strength_label(512) == "Excellent"


def test_passwords_are_randomized_not_repeated():
    options = CharsetOptions()
    passwords = {generate_for_entropy_target(options, 128)[0] for _ in range(20)}
    assert len(passwords) == 20
