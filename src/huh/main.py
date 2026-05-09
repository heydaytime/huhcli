#!/usr/bin/env python3

import os
import platform
import subprocess
from typing import Optional, List
import typer
from rich import print
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

from huh.paths import data_path
from huh.ai import (
    get_correction,
    record_accepted,
    is_ollama_installed,
    list_local_models,
    get_selected_model,
    set_selected_model,
    is_initialized,
    append_stored,
)

_plain = Console(highlight=False)
app = typer.Typer()


def _storage_path() -> str:
    return data_path("storage.txt")


def read_history(path: Optional[str] = None) -> List[str]:
    p = path or _storage_path()
    try:
        with open(p, "r") as f:
            raw_lines = f.readlines()
    except FileNotFoundError:
        return []

    joined: List[str] = []
    current = ""
    for line in raw_lines:
        line = line.rstrip("\n")
        if line.rstrip().endswith("\\"):
            current += line.rstrip()[:-1].rstrip() + " "
        else:
            current += line
            stripped = current.strip()
            if stripped:
                joined.append(stripped)
            current = ""
    if current.strip():
        joined.append(current.strip())

    return joined


def get_failed_command(history: List[str]) -> Optional[str]:
    skip_prefixes = (
        "huh", "python -m huh", "typer ./src/huh", "pip install", "./clean.zsh",
        "source ", ". ", "export ", "eval ", "alias ", "unalias ",
        "setopt ", "unsetopt ", "clear", "exit", "history", "fc ",
        "bindkey ", "zstyle ", "autoload ", "compinit", "typeset ",
    )
    for cmd in reversed(history):
        if not any(cmd.startswith(p) for p in skip_prefixes):
            return cmd
    return history[-1] if history else None


def _run_command(cmd: str) -> None:
    user_shell = os.environ.get("SHELL", "/bin/sh")
    try:
        subprocess.run([user_shell, "-c", cmd])
    except KeyboardInterrupt:
        print()
        raise typer.Exit(0)


def _ensure_platform() -> None:
    if platform.system() == "Windows":
        print("[red]Windows is not supported.[/red]")
        raise typer.Exit(1)


def _ensure_ollama() -> None:
    if not is_ollama_installed():
        print("[red]Ollama is not running or not installed.[/red]")
        print("")
        print("[yellow]Please install Ollama first:[/yellow]")
        print("  https://ollama.com/download")
        print("")
        print("Then pull a model, for example:")
        print("  ollama pull llama3.2:3b")
        raise typer.Exit(1)


def _ensure_initialized() -> None:
    if not is_initialized():
        print("[yellow]huh has not been initialized yet.[/yellow]")
        print("")
        print("Please select a model first by running:")
        print("  huhcli select")
        raise typer.Exit(1)


def _detect_shell() -> str:
    shell = os.environ.get("SHELL", "")
    if "bash" in shell:
        return "bash"
    return "zsh"


def _rc_file(shell: str) -> str:
    return os.path.expanduser("~/.bashrc") if shell == "bash" else os.path.expanduser("~/.zshrc")


def _shell_function(shell: str) -> str:
    storage = os.path.join(
        os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
        "huh",
        "storage.txt",
    )
    if shell == "bash":
        history_cmd = f'history | tail -n 1000 | sed "s/^[ ]*[0-9]*[ ]*//" > "{storage}"'
    else:
        history_cmd = f'fc -ln 1 | tail -n 1000 > "{storage}"'

    return f"""
# === huhcli shell wrapper (auto-installed) ===
function huhcli() {{
  {history_cmd}
  if [ $# -eq 0 ]; then
    command huhcli correct
  else
    command huhcli "$@"
  fi
}}
# === end huhcli ===
"""


@app.command(help="Install the huhcli shell wrapper into your ~/.zshrc or ~/.bashrc.")
def setup():
    _ensure_platform()
    shell = _detect_shell()
    rc = _rc_file(shell)

    func = _shell_function(shell)

    existing = ""
    if os.path.exists(rc):
        with open(rc, "r") as f:
            existing = f.read()

    # Remove old wrapper if present
    marker_start = "# === huhcli shell wrapper"
    marker_end = "# === end huhcli ==="
    if marker_start in existing:
        start = existing.find(marker_start)
        end = existing.find(marker_end, start) + len(marker_end)
        existing = existing[:start] + existing[end:]
        existing = existing.rstrip() + "\n"

    # Append new wrapper
    with open(rc, "w") as f:
        f.write(existing.rstrip() + "\n" + func + "\n")

    print(f"[green]Installed huhcli shell wrapper into {rc}[/green]")
    print("")
    print("Please reload your shell:")
    print(f"  source {rc}")
    print("")
    print("Then run [bold]huhcli select[/bold] to choose your AI model.")


@app.command(help="Choose which local Ollama model to use for corrections. Required on first run.")
def select():
    _ensure_platform()
    _ensure_ollama()

    try:
        models = list_local_models()
    except RuntimeError as e:
        print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if not models:
        print("[red]No local models found.[/red]")
        print("")
        print("Please pull a model first, for example:")
        print("  ollama pull llama3.2:3b")
        raise typer.Exit(1)

    current = get_selected_model()
    print("[bold]Available local models:[/bold]")
    for i, m in enumerate(models, 1):
        marker = " [green](current)[/green]" if m == current else ""
        _plain.print(f"  {i}. {m}{marker}")

    choice = Prompt.ask("Select a model by number or name")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            selected = models[idx]
        else:
            selected = choice.strip()
    except ValueError:
        selected = choice.strip()

    if selected not in models:
        print(f"[yellow]Warning: '{selected}' is not in the list of local models.[/yellow]")
        confirm = Prompt.ask("Continue anyway?", choices=["y", "n"], default="n")
        if confirm != "y":
            print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    set_selected_model(selected)
    _plain.print(f"[green]Selected model: {selected}[/green]")


@app.command(help="Save the last N commands from your shell history so the AI can reference them later.")
def store(n: int):
    _ensure_platform()

    history = read_history()
    if not history:
        print("[red]No history found.[/red]")
        raise typer.Exit(1)

    if n <= 0:
        print("[red]n must be a positive integer.[/red]")
        raise typer.Exit(1)

    skip_prefixes = (
        "huh", "python -m huh", "typer ./src/huh", "pip install", "./clean.zsh",
        "source ", ". ", "export ", "eval ", "alias ", "unalias ",
        "setopt ", "unsetopt ", "clear", "exit", "history", "fc ",
        "bindkey ", "zstyle ", "autoload ", "compinit", "typeset ",
    )

    recent = history[-n:]
    filtered = []
    seen = set()
    for cmd in recent:
        if any(cmd.startswith(p) for p in skip_prefixes):
            continue
        if cmd in seen:
            continue
        seen.add(cmd)
        filtered.append(cmd)

    if not filtered:
        print("[yellow]No commands to store after filtering.[/yellow]")
        raise typer.Exit(0)

    append_stored(filtered)
    print(f"[green]Stored {len(filtered)} command(s).[/green]")


@app.command(help="Suggest a fix for your last failed shell command using a local AI model.")
def correct(
    last: Optional[str] = typer.Option(None, "--last", help="The failed command to correct"),
):
    _ensure_platform()
    _ensure_ollama()
    _ensure_initialized()

    try:
        history = read_history()
        failed = last or get_failed_command(history)

        if not failed:
            print("[red]No failed command found.[/red]")
            raise typer.Exit(1)

        print(f"[dim]Failed command:[/dim] [yellow]{failed}[/yellow]")
        print("[dim]Asking Ollama...[/dim]")

        try:
            suggestion = get_correction(failed, history)
        except RuntimeError as e:
            print(f"[red]{e}[/red]")
            raise typer.Exit(1)

        if not suggestion:
            print("[red]AI returned an empty suggestion.[/red]")
            raise typer.Exit(1)

        if "->" in suggestion:
            suggestion = suggestion.split("->")[-1].strip()

        if suggestion.strip().lower() == failed.strip().lower():
            print(Panel(f"[yellow]{suggestion}[/yellow]", title="AI thinks this is already correct", border_style="yellow"))
            print("[yellow]No obvious typo detected. You can still run it if you want.[/yellow]")
        else:
            print(Panel(f"[green]{suggestion}[/green]", title="Suggested command", border_style="green"))

        choice = Prompt.ask(
            "[bold]Run (r), Copy (c), Save & Run (s), or Quit (q)?[/bold]",
            choices=["r", "c", "s", "q"],
            default="r",
            show_choices=True,
        )

        if choice == "r":
            print(f"[dim]Running: {suggestion}[/dim]")
            _run_command(suggestion)
        elif choice == "c":
            try:
                subprocess.run(["pbcopy"], input=suggestion.encode(), check=True)
                print("[green]Copied to clipboard.[/green]")
            except Exception:
                print("[yellow]Could not copy to clipboard.[/yellow]")
        elif choice == "s":
            record_accepted(failed, suggestion)
            print(f"[dim]Running: {suggestion}[/dim]")
            _run_command(suggestion)
            print("[green]Saved correction to accepted history.[/green]")
        elif choice == "q":
            print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)
    except KeyboardInterrupt:
        print()
        raise typer.Exit(0)


@app.command(help="Show the last N commands captured from your shell history.")
def history_cmd(n: Optional[str] = None):
    try:
        with open(_storage_path(), "r") as f:
            lines = f.readlines()
            length = len(lines)
    except FileNotFoundError:
        return typer.echo("storage.txt not found.")
    def_val = 4
    try:
        n_int = int(n) if n is not None else def_val
    except ValueError:
        return typer.echo("Please provide a valid integer for n.")
    if length < def_val:
        num = length
    else:
        num = n_int if n_int < length else def_val

    commands = lines[-num:]
    print("Last commands:")
    for cmd in commands:
        print(cmd.strip())


if __name__ == "__main__":
    app(prog_name="huhcli")
