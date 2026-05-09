# huhcli — AI CLI Syntax Autocorrector

**huhcli** is a lightweight shell assistant that suggests corrections for mistyped or failed CLI commands using a local LLM via [Ollama](https://ollama.com).

When a command fails, run `huhcli`. It reads your recent shell history, detects the most likely failed command, asks a local model for a fix, and lets you run, copy, or save the suggestion instantly.

---

## How It Works

1. **Capture history** — `huhcli` snapshots the last 1000 commands from your shell history.
2. **Detect the failure** — It skips internal/meta commands (e.g., `source`, `export`, `huhcli` itself) and picks the most recent real command as the one to correct.
3. **Ask the model** — A few-shot prompt is built from your recent history, previously accepted corrections, and fuzzy-matched stored commands, then sent to your local Ollama instance.
4. **Interact** — You get a suggested fix and can choose to:
   - **(r)** Run it immediately
   - **(c)** Copy it to your clipboard
   - **(s)** Save the correction pair and run it (improves future suggestions)
   - **(q)** Quit

---

## Requirements

- **macOS or Linux**
- **zsh or bash**
- **Python** >= 3.9
- **[Ollama](https://ollama.com)** running locally

---

## Installation

### macOS (Homebrew)

```bash
brew tap heydaytime/huhcli
brew install huhcli
```

### Linux (One-liner)

```bash
curl -fsSL https://raw.githubusercontent.com/heydaytime/huhcli/main/install.sh | bash
```

### Manual (any platform)

```bash
git clone https://github.com/heydaytime/huhcli.git
cd huhcli
python -m venv venv
source venv/bin/activate
pip install .
python -m huh setup
source ~/.zshrc   # or ~/.bashrc
```

---

## Shell Setup

After installation, run the setup command to install the shell wrapper:

```bash
huhcli setup
```

Reload your shell:

```bash
source ~/.zshrc   # or source ~/.bashrc
```

This registers the `huhcli` function, which captures your shell history before invoking the corrector.

---

## First-Time Setup

After installation, choose which local Ollama model to use:

```bash
huhcli select
```

This lists every model you have pulled locally and lets you pick one. Your choice is saved to `~/.config/huh/config.json` and will be used for all future corrections. You can change it anytime by running `huhcli select` again.

---

## Usage

After a command fails or you mistype something, simply run:

```bash
huhcli
```

**Example interaction:**

```bash
$ gti status
zsh: command not found: gti
$ huhcli
Failed command: gti status
Asking Ollama...
╭──────── Suggested command ────────╮
│ git status                        │
╰───────────────────────────────────╯
Run (r), Copy (c), Save & Run (s), or Quit (q)? [r]:
```

---

## Commands

| Command | Description |
|---------|-------------|
| `huhcli` | Detect the last failed command and suggest a correction. |
| `huhcli setup` | Install the shell wrapper into your rc file. Run once after installing. |
| `huhcli select` | Choose which local Ollama model to use. Required on first run. |
| `huhcli store <n>` | Save the last `n` commands to the fuzzy matching cache. |
| `huhcli history [n]` | Show the last `n` commands from captured history (default: 4). |
| `huhcli stored` | Show the commands currently in the fuzzy matching cache. |

---

## Data Locations

User data is stored in standard XDG directories:

| File | Location |
|------|----------|
| Config (selected model) | `~/.config/huh/config.json` |
| Shell history snapshot | `~/.local/share/huh/storage.txt` |
| Accepted corrections | `~/.local/share/huh/accepted.json` |
| Stored commands (fuzzy cache) | `~/.local/share/huh/stored_commands.json` |

---

## Configuration

You can customize behavior via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | URL of your Ollama server. |

---

## How Suggestions Improve Over Time

Whenever you choose **Save & Run (s)**, the pair `(wrong_command -> corrected_command)` is stored in `accepted.json`. On future runs, the top 10 accepted corrections are injected into the prompt as extra context, so the model learns from your preferences and common typos.

The prompt also includes your last 15 real commands as additional context.

---

## License

MIT
