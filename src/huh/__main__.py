#!/usr/bin/env python3

import sys
import os
import subprocess

HUHCLI_PATH = os.environ.get(
    "HUHCLI_PATH",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)


def print_alias():
    print("""
function huhcli() {
  source "$HUHCLI_PATH/venv/bin/activate"
  fc -ln 1 | tail -n 64 > "$HUHCLI_PATH/storage.txt"
  python -m huh correct
}
""")


if __name__ == "__main__":
    try:
        if "--alias" in sys.argv:
            print_alias()
        elif "--store" in sys.argv:
            with open(os.path.join(HUHCLI_PATH, "storage.txt"), "w") as f:
                f.write(" ".join(sys.argv[2:]))
        else:
            main_path = os.path.join(os.path.dirname(__file__), "main.py")
            subprocess.run([sys.executable, main_path] + sys.argv[1:])
    except KeyboardInterrupt:
        sys.exit(0)
