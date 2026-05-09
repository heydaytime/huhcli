#!/usr/bin/env python3

import sys
import os
import subprocess

from huh.paths import data_path

HUHCLI_PATH = os.environ.get(
    "HUHCLI_PATH",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)


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
    fc -ln 1 | tail -n 1000 > "{data_path('storage.txt')}"
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
            with open(data_path("storage.txt"), "w") as f:
                f.write(" ".join(sys.argv[2:]))
        else:
            main_path = os.path.join(os.path.dirname(__file__), "main.py")
            subprocess.run([sys.executable, main_path] + sys.argv[1:])
    except KeyboardInterrupt:
        sys.exit(0)
