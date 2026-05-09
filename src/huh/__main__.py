#!/usr/bin/env python3

import sys
import os
import subprocess

if __name__ == "__main__":
    try:
        main_path = os.path.join(os.path.dirname(__file__), "main.py")
        subprocess.run([sys.executable, main_path] + sys.argv[1:])
    except KeyboardInterrupt:
        sys.exit(0)
