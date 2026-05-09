#!/usr/bin/env python3

import os
import subprocess
from typing import Optional, List
import typer
from rich import print
from rich.prompt import Prompt
from rich.panel import Panel

from huh.ai import get_correction, record_accepted

app = typer.Typer()


def _base_dir() -> str:
    return os.environ.get("HUHCLI_PATH", os.getcwd())


def _storage_path() -> str:
    return os.path.join(_base_dir(), "storage.txt")


def read_history(path: Optional[str] = None) -> List[str]:
    p = path or _storage_path()
    try:
        with open(p, "r") as f:
            raw_lines = f.readlines()
    except FileNotFoundError:
        return []

    # fc outputs multi-line commands as separate lines ending with \
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
        # tool internals
        "huh", "python -m huh", "typer ./src/huh", "pip install", "./clean.zsh",
        # shell meta-commands / config reloads
        "source ", ". ", "export ", "eval ", "alias ", "unalias ",
        "setopt ", "unsetopt ", "clear", "exit", "history", "fc ",
        "bindkey ", "zstyle ", "autoload ", "compinit", "typeset ",
    )
    for cmd in reversed(history):
        if not any(cmd.startswith(p) for p in skip_prefixes):
            return cmd
    return history[-1] if history else None


def _run_command(cmd: str) -> None:
    """Run a command using the user's actual shell (e.g. zsh) instead of /bin/sh."""
    user_shell = os.environ.get("SHELL", "/bin/sh")
    try:
        subprocess.run([user_shell, "-c", cmd])
    except KeyboardInterrupt:
        # User interrupted the running command (e.g. ^C on ping). Exit cleanly.
        print()
        raise typer.Exit(0)


@app.command()
def correct(
    last: Optional[str] = typer.Option(None, "--last", help="The failed command to correct"),
):
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

        # If the model echoes the few-shot format, extract just the corrected part
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


@app.command()
def hello(name: str):
    print(f"Hello {name}!")


@app.command()
def analyze(n: Optional[str] = None):
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
