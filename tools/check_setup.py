"""Check that your machine is ready for the course.

Run from the repo root:

    python3 tools/check_setup.py

Uses only the standard library, so it works before you have installed anything else.
Required tools must pass; optional tools only unlock some labs.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GREEN, YELLOW, RED, RESET = "\033[32m", "\033[33m", "\033[31m", "\033[0m"


def run(cmd: list[str], timeout: int = 20) -> tuple[bool, str]:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        text = (out.stdout or out.stderr).strip().splitlines()
        return out.returncode == 0, text[0] if text else ""
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)


def check_python() -> tuple[bool, str]:
    v = sys.version_info
    return v >= (3, 11), f"Python {v.major}.{v.minor}.{v.micro} (need 3.11+)"


def check_tool(name: str, args: list[str]) -> tuple[bool, str]:
    if shutil.which(name) is None:
        return False, f"{name} not found on PATH"
    return run([name, *args])


def check_docker_daemon() -> tuple[bool, str]:
    if shutil.which("docker") is None:
        return False, "docker not found on PATH"
    ok, msg = run(["docker", "info", "--format", "{{.ServerVersion}}"])
    return ok, f"Docker daemon running (server {msg})" if ok else "Docker installed but daemon not running: start Docker Desktop / dockerd"


def check_ollama_model() -> tuple[bool, str]:
    if shutil.which("ollama") is None:
        return False, "ollama not installed (labs fall back to the fake LLM)"
    ok, _ = run(["ollama", "list"])
    if not ok:
        return False, "ollama installed but not running: run `ollama serve`"
    out = subprocess.run(["ollama", "list"], capture_output=True, text=True).stdout
    models = [line.split()[0] for line in out.splitlines()[1:] if line.strip()]
    if not models:
        return False, "ollama running, no models yet: `ollama pull qwen2.5:1.5b-instruct`"
    return True, f"ollama models: {', '.join(models[:4])}"


def check_dataset_generator() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        ok, msg = run(
            [sys.executable, str(REPO_ROOT / "datasets/fraud/generate.py"), "--rows", "1000", "--out", f"{tmp}/t.csv"]
        )
    return ok, msg or "generator failed"


REQUIRED = [
    ("Python", check_python),
    ("uv", lambda: check_tool("uv", ["--version"])),
    ("Git", lambda: check_tool("git", ["--version"])),
    ("Dataset generator", check_dataset_generator),
]
OPTIONAL = [
    ("Docker (Modules 1, 4, 6)", check_docker_daemon),
    ("Ollama + a local model (real LLM answers)", check_ollama_model),
    ("kubectl (Module 6)", lambda: check_tool("kubectl", ["version", "--client"])),
    ("kind (Module 6 local cluster)", lambda: check_tool("kind", ["version"])),
]


def main() -> int:
    print("\n🏭 Build Production-Grade AI Systems: setup check\n")
    failed = 0
    for label, fn in REQUIRED:
        ok, msg = fn()
        failed += not ok
        print(f"  {GREEN + '✔' if ok else RED + '✘'}{RESET} {label:<45} {msg}")
    print()
    for label, fn in OPTIONAL:
        ok, msg = fn()
        print(f"  {GREEN + '✔' if ok else YELLOW + '•'}{RESET} {label:<45} {msg}")
    print()
    if failed:
        print(f"{RED}{failed} required check(s) failed.{RESET} See modules/00-foundations/01-setup-your-workbench.md\n")
        return 1
    print(f"{GREEN}You're ready. Start with Module 0 → modules/00-foundations/README.md{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
