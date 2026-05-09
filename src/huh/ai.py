#!/usr/bin/env python3

import difflib
import os
import json
import requests
from typing import List, Dict, Tuple

from huh.paths import config_path, data_path

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_URL = OLLAMA_HOST + "/api/generate"
DEFAULT_MODEL = os.environ.get("HUH_MODEL", "llama3.2:3b")

FUZZY_MATCH_THRESHOLD = 0.4


def load_config() -> Dict:
    path = config_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config: Dict) -> None:
    path = config_path()
    with open(path, "w") as f:
        json.dump(config, f, indent=2)


def is_initialized() -> bool:
    config = load_config()
    return config.get("initialized", False) and bool(config.get("model"))


def get_selected_model() -> str:
    config = load_config()
    return config.get("model", DEFAULT_MODEL)


def set_selected_model(model: str) -> None:
    config = load_config()
    config["model"] = model
    config["initialized"] = True
    save_config(config)


def is_ollama_installed() -> bool:
    try:
        resp = requests.get(OLLAMA_HOST + "/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def list_local_models() -> List[str]:
    try:
        resp = requests.get(OLLAMA_HOST + "/api/tags", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("models", [])
        names = []
        for m in models:
            name = m.get("name") or m.get("model")
            if name:
                names.append(name)
        return names
    except Exception as e:
        raise RuntimeError(f"Could not list local models: {e}")


def _stored_path() -> str:
    return data_path("stored_commands.json")


def load_stored() -> List[str]:
    path = _stored_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_stored(stored: List[str]) -> None:
    path = _stored_path()
    with open(path, "w") as f:
        json.dump(stored, f, indent=2)


def append_stored(commands: List[str]) -> None:
    stored = load_stored()
    existing = set(stored)
    for cmd in commands:
        if cmd not in existing:
            stored.append(cmd)
            existing.add(cmd)
    if len(stored) > 1000:
        stored = stored[-1000:]
    save_stored(stored)


def find_similar_commands(failed_cmd: str, top_n: int = 3) -> List[str]:
    stored = load_stored()
    if not stored:
        return []

    scored: List[Tuple[float, str]] = []
    for cmd in stored:
        ratio = difflib.SequenceMatcher(None, failed_cmd.lower(), cmd.lower()).ratio()
        if ratio >= FUZZY_MATCH_THRESHOLD:
            scored.append((ratio, cmd))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [cmd for _, cmd in scored[:top_n]]


def _accepted_path() -> str:
    return data_path("accepted.json")


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
    similar = find_similar_commands(failed_cmd)

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

    if similar:
        lines.append("Similar commands you have used before:")
        for cmd in similar:
            lines.append(f"  {cmd}")
        lines.append("")

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
        "model": get_selected_model(),
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
