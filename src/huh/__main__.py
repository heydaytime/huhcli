#!/usr/bin/env python3

import sys
import os
import subprocess

HUHCLI_PATH = os.environ.get(
    "HUHCLI_PATH",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)


def _data_dir() -> str:
    base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    path = os.path.join(base, "huh")
    os.makedirs(path, exist_ok=True)
    return path


def _storage_path() -> str:
    return os.path.join(_data_dir(), "storage.txt")


def _detect_shell() -> str:
    if "--shell" in sys.argv:
        idx = sys.argv.index("--shell")
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    shell = os.environ.get("SHELL", "")
    if "bash" in shell:
        return "bash"
    return "zsh"


def print_alias(shell: str):
    if shell == "bash":
        rc_file = "~/.bashrc"
    else:
        rc_file = "~/.zshrc"

    print(f"""
# Add the following to your {rc_file}:
function huhcli() {{
  local HUH_PYTHON="$HUHCLI_PATH/venv/bin/python"
  source "$HUHCLI_PATH/venv/bin/activate"
  if [ $# -eq 0 ]; then
    fc -ln 1 | tail -n 1000 > "{_storage_path()}"
    "$HUH_PYTHON" -m huh correct
  else
    "$HUH_PYTHON" -m huh "$@"
  fi
}}
""")


if __name__ == "__main__":
    try:
        if "--alias" in sys.argv:
            shell = _detect_shell()
            print_alias(shell)
        elif "--store" in sys.argv:
            with open(_storage_path(), "w") as f:
                f.write(" ".join(sys.argv[2:]))
        else:
            main_path = os.path.join(os.path.dirname(__file__), "main.py")
            subprocess.run([sys.executable, main_path] + sys.argv[1:])
    except KeyboardInterrupt:
        sys.exit(0)
