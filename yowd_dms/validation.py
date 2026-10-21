"""Small reusable input-validation helpers for the textual UI.

Centralised here so every menu enforces the same rules: no blank
required fields, numeric fields must actually parse as numbers, and
choices must be one of the offered options.
"""
from __future__ import annotations


def prompt_nonblank(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print("  -> This field cannot be blank. Please try again.")


def prompt_float(label: str, min_value: float = 0.0) -> float:
    while True:
        raw = input(f"{label}: ").strip()
        try:
            value = float(raw)
        except ValueError:
            print("  -> Please enter a valid number.")
            continue
        if value < min_value:
            print(f"  -> Value must be at least {min_value}.")
            continue
        return value


def prompt_choice(label: str, options: list) -> str:
    option_str = "/".join(options)
    while True:
        raw = input(f"{label} ({option_str}): ").strip().lower()
        for opt in options:
            if raw == opt.lower():
                return opt
        print(f"  -> Please enter one of: {option_str}")


def prompt_yes_no(label: str) -> bool:
    while True:
        raw = input(f"{label} (y/n): ").strip().lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  -> Please enter 'y' or 'n'.")
