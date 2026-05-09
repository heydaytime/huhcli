#!/usr/bin/env python3

import os
import json
import requests
from typing import List, Dict

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434") + "/api/generate"
DEFAULT_MODEL = os.environ.get("HUH_MODEL", "llama3.2:3b")


def _base_dir() -> str:
    return os.environ.get("HUHCLI_PATH", os.getcwd())


def _accepted_path() -> str:
    return os.path.join(_base_dir(), "accepted.json")


def _load_accepted() -> List[Dict[str, str]]:
    path = _accepted_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_accepted(accepted: List[Dict[str, str]]) -> None:
    path = _accepted_path()
    with open(path, "w") as f:
        json.dump(accepted, f, indent=2)


def build_prompt(failed_cmd: str, history: List[str], accepted: List[Dict[str, str]]) -> str:
    recent_history = history[-15:]
    recent_accepted = accepted[-10:]

    lines = [
        "You are a shell command autocorrector.",
        "Given a failed or mistyped shell command, suggest the corrected command.",
        "Output ONLY the corrected command, with no explanation, markdown, bullets, or quotes.",
        "",
        "Example 1:",
        "Failed command: gti status",
        "Corrected command: git status",
        "",
        "Example 2:",
        "Failed command: cd..",
        "Corrected command: cd ..",
        "",
        "Example 3:",
        "Failed command: mdkir myfolder",
        "Corrected command: mkdir myfolder",
        "",
        "Example 4:",
        "Failed command: png google.com",
        "Corrected command: ping google.com",
        "",
        "Example 5:",
        "Failed command: sl",
        "Corrected command: ls",
        "",
    ]

    if recent_accepted:
        lines.append("Previously accepted corrections:")
        for item in recent_accepted:
            lines.append(f"  {item['wrong']} -> {item['right']}")
        lines.append("")

    if recent_history:
        lines.append("Recent shell history:")
        for cmd in recent_history:
            lines.append(f"  {cmd}")
        lines.append("")

    lines.extend([
        f"Failed command: {failed_cmd}",
        "",
        "Corrected command:",
    ])

    return "\n".join(lines)


def get_correction(failed_cmd: str, history: List[str]) -> str:
    accepted = _load_accepted()
    prompt = build_prompt(failed_cmd, history, accepted)

    payload = {
        "model": DEFAULT_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 50,
        },
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        correction = data.get("response", "").strip()
        # Take only the first non-empty line to ignore any trailing notes
        for line in correction.splitlines():
            line = line.strip()
            if line:
                correction = line
                break
        # Strip common formatting artifacts
        correction = correction.strip("`").strip()
        if correction.startswith("$ "):
            correction = correction[2:]
        return correction
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Could not connect to Ollama. Is it running?")
    except Exception as e:
        raise RuntimeError(f"Ollama request failed: {e}")


def record_accepted(wrong: str, right: str) -> None:
    accepted = _load_accepted()
    accepted.append({"wrong": wrong, "right": right})
    _save_accepted(accepted)
