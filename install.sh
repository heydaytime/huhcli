#!/usr/bin/env bash
set -euo pipefail

echo "=== huh installer ==="

# Detect OS
OS="$(uname -s)"

# Detect shell
CURRENT_SHELL="$(basename "$SHELL")"
if [ "$CURRENT_SHELL" = "bash" ]; then
    RC_FILE="$HOME/.bashrc"
else
    RC_FILE="$HOME/.zshrc"
fi

STORAGE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/huh"
mkdir -p "$STORAGE_DIR"

install_macos() {
    if ! command -v brew >/dev/null 2>&1; then
        echo "[ERROR] Homebrew is required but not installed."
        echo "Install it from https://brew.sh and rerun this script."
        exit 1
    fi

    echo "Installing via Homebrew..."
    brew tap heydaytime/huhcli
    brew install huhcli
}

install_linux() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[ERROR] Python 3 is required but not installed."
        echo "Install it with your package manager (e.g., sudo apt install python3) and rerun."
        exit 1
    fi

    PYTHON="$(command -v python3)"

    # Check venv module is available
    if ! "$PYTHON" -m venv --help >/dev/null 2>&1; then
        echo "[ERROR] python3-venv is not installed."
        echo "Install it with: sudo apt install python3-venv"
        exit 1
    fi

    INSTALL_DIR="$HOME/.local/lib/huhcli"
    VENV_DIR="$INSTALL_DIR/venv"
    BIN_DIR="$HOME/.local/bin"

    echo "Installing huhcli to $INSTALL_DIR ..."
    rm -rf "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"

    # Download latest release
    TMPDIR="$(mktemp -d)"
    TARBALL="$TMPDIR/huhcli.tar.gz"

    echo "Downloading huhcli..."
    if ! curl -fsSL "https://github.com/heydaytime/huhcli/archive/refs/tags/v0.1.4.tar.gz" -o "$TARBALL"; then
        echo "[ERROR] Failed to download huhcli. Check your internet connection."
        rm -rf "$TMPDIR"
        exit 1
    fi

    echo "Extracting..."
    tar -xzf "$TARBALL" -C "$TMPDIR"

    # Find extracted directory
    EXTRACTED_DIR="$(find "$TMPDIR" -maxdepth 1 -type d -name 'huhcli-*' | head -n 1)"
    if [ -z "$EXTRACTED_DIR" ]; then
        echo "[ERROR] Could not find extracted huhcli directory."
        rm -rf "$TMPDIR"
        exit 1
    fi

    # Create venv
    echo "Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"

    # Install into venv
    echo "Installing into virtual environment..."
    if ! "$VENV_DIR/bin/pip" install "$EXTRACTED_DIR"; then
        echo "[ERROR] pip install failed."
        rm -rf "$TMPDIR" "$INSTALL_DIR"
        exit 1
    fi

    rm -rf "$TMPDIR"

    # Create wrapper script that uses venv python
    mkdir -p "$BIN_DIR"
    cat > "$BIN_DIR/huh" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" -m huh "\$@"
EOF
    chmod +x "$BIN_DIR/huh"

    # Ensure ~/.local/bin is on PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo ""
        echo "[WARNING] $HOME/.local/bin is not in your PATH."
        echo "Add this to your $RC_FILE:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo "Then reload your shell."
    fi

    echo "Installed binary to $BIN_DIR/huh"
}

# Main install
if [ "$OS" = "Darwin" ]; then
    install_macos
elif [ "$OS" = "Linux" ]; then
    install_linux
else
    echo "[ERROR] Unsupported OS: $OS"
    exit 1
fi

# Install shell wrapper
FUNC_BLOCK="
# === huh shell wrapper (auto-installed) ===
function huh() {
  if [ \$# -eq 0 ]; then
    if [ -n \"\$BASH_VERSION\" ]; then
      history | tail -n 1000 | sed 's/^[ ]*[0-9]*[ ]*//' > \"$STORAGE_DIR/storage.txt\"
    else
      fc -ln 1 | tail -n 1000 > \"$STORAGE_DIR/storage.txt\"
    fi
    command huh correct
  else
    command huh \"\$@\"
  fi
}
# === end huh ==="

if grep -q "# === huh shell wrapper" "$RC_FILE" 2>/dev/null; then
    echo "Shell wrapper already present in $RC_FILE"
else
    echo "$FUNC_BLOCK" >> "$RC_FILE"
    echo "Added shell wrapper to $RC_FILE"
fi

echo ""
echo "=== Installation complete ==="
echo "Reload your shell:"
echo "  source $RC_FILE"
echo ""
echo "Then select an Ollama model:"
echo "  huh select"
echo ""
echo "Make sure Ollama is running before using huh."
