#!/usr/bin/env python3

"""Path utilities for standard XDG directories."""

import os


def _config_dir() -> str:
    base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    path = os.path.join(base, "huh")
    os.makedirs(path, exist_ok=True)
    return path


def _data_dir() -> str:
    base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    path = os.path.join(base, "huh")
    os.makedirs(path, exist_ok=True)
    return path


def config_path() -> str:
    return os.path.join(_config_dir(), "config.json")


def data_path(filename: str) -> str:
    return os.path.join(_data_dir(), filename)
