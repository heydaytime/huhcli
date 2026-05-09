#!/usr/bin/env bash
set -e

echo "=== huhcli installer ==="

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
        echo "Homebrew is required but not installed."
        echo "Install it from https://brew.sh and rerun this script."
        exit 1
    fi

    echo "Installing via Homebrew..."
    brew tap heydaytime/huhcli
    brew install huhcli
}

install_linux() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "Python 3 is required but not installed."
        echo "Install it with your package manager (e.g., apt install python3) and rerun."
        exit 1
    fi

    PYTHON="$(command -v python3)"
    INSTALL_DIR="$HOME/.local/lib/huhcli"
    BIN_DIR="$HOME/.local/bin"

    echo "Installing huhcli to $INSTALL_DIR ..."
    rm -rf "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"

    # Download latest release tarball
    TMPDIR="$(mktemp -d)"
    curl -fsSL \
        "https://github.com/heydaytime/huhcli/archive/refs/tags/v0.1.2.tar.gz" \
        -o "$TMPDIR/huhcli.tar.gz"

    tar -xzf "$TMPDIR/huhcli.tar.gz" -C "$TMPDIR"
    mv "$TMPDIR/huhcli-0.1.2/src/huh" "$INSTALL_DIR/"
    rm -rf "$TMPDIR"

    # Create wrapper script
    mkdir -p "$BIN_DIR"
    cat > "$BIN_DIR/huhcli" <<'EOF'
#!/usr/bin/env bash
exec python3 -m huh "$@"
EOF
    chmod +x "$BIN_DIR/huhcli"

    # Ensure ~/.local/bin is on PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo ""
        echo "[WARNING] $HOME/.local/bin is not in your PATH."
        echo "Add this to your $RC_FILE:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi

    echo "Installed binary to $BIN_DIR/huhcli"
}

# Main install
if [ "$OS" = "Darwin" ]; then
    install_macos
elif [ "$OS" = "Linux" ]; then
    install_linux
else
    echo "Unsupported OS: $OS"
    exit 1
fi

# Install shell wrapper
FUNC_BLOCK="
# === huhcli shell wrapper (auto-installed) ===
function huhcli() {
  if [ \$# -eq 0 ]; then
    if [ -n \"\$BASH_VERSION\" ]; then
      history | tail -n 1000 | sed 's/^[ ]*[0-9]*[ ]*//' > \"$STORAGE_DIR/storage.txt\"
    else
      fc -ln 1 | tail -n 1000 > \"$STORAGE_DIR/storage.txt\"
    fi
    command huhcli correct
  else
    command huhcli \"\$@\"
  fi
}
# === end huhcli ==="

if grep -q "# === huhcli shell wrapper" "$RC_FILE" 2>/dev/null; then
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
echo "  huhcli select"
echo ""
echo "Make sure Ollama is running before using huhcli."
