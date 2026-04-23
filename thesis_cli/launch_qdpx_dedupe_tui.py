#!/usr/bin/env python3
"""Launch the QDPX dedupe TUI.

By default it runs in the current terminal. With --new-window, it tries to
launch in a new terminal window/tab, then falls back to current terminal.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def _find_qdpx_candidates(workspace_root: Path) -> list[Path]:
    qdpx_dir = workspace_root / "qdpx"
    candidates: list[Path] = []
    if qdpx_dir.exists():
        candidates.extend(qdpx_dir.glob("*.qdpx"))
    candidates.extend(workspace_root.glob("*.qdpx"))
    # Deduplicate while preserving first-seen order.
    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    deduped.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return deduped


def _pick_qdpx_interactive(candidates: list[Path], workspace_root: Path) -> Path:
    if not candidates:
        raise FileNotFoundError("No .qdpx file found in ./qdpx or workspace root.")
    if len(candidates) == 1:
        return candidates[0]

    if not sys.stdin.isatty():
        print("No --qdpx provided and no interactive terminal; using newest .qdpx file.")
        return candidates[0]

    print("Select a QDPX file:")
    for idx, candidate in enumerate(candidates, start=1):
        try:
            rel = candidate.resolve().relative_to(workspace_root.resolve())
            display = str(rel)
        except ValueError:
            display = str(candidate)
        print(f"  {idx}) {display}")

    while True:
        raw = input(f"Enter number [1-{len(candidates)}] (blank=1): ").strip()
        if raw == "":
            return candidates[0]
        try:
            selected = int(raw)
        except ValueError:
            print("Please enter a valid number.")
            continue
        if 1 <= selected <= len(candidates):
            return candidates[selected - 1]
        print("Selection out of range.")


def _resolve_poetry_path() -> str | None:
    poetry_path = shutil.which("poetry")
    if poetry_path:
        return poetry_path
    return None


def _build_inner_command(
    workspace_root: Path,
    qdpx_path: Path,
    passthrough: list[str],
    poetry_path: str | None,
) -> str:
    if poetry_path:
        base = [poetry_path, "run", "qdpx-dedupe", "--qdpx", str(qdpx_path)]
    else:
        python_path = Path(sys.executable).resolve()
        script_path = workspace_root / "thesis_cli" / "qdpx_dedupe_tui.py"
        base = [str(python_path), str(script_path), "--qdpx", str(qdpx_path)]
    full = [*base, *passthrough]
    quoted = " ".join(shlex.quote(part) for part in full)
    return f"cd {shlex.quote(str(workspace_root))} && {quoted}"


def _build_powershell_command(
    workspace_root: Path,
    qdpx_path: Path,
    passthrough: list[str],
    poetry_path: str | None,
) -> str:
    if poetry_path:
        parts = [
            poetry_path,
            "run",
            "qdpx-dedupe",
            "--qdpx",
            str(qdpx_path),
            *passthrough,
        ]
    else:
        python_path = Path(sys.executable).resolve()
        script_path = workspace_root / "thesis_cli" / "qdpx_dedupe_tui.py"
        parts = [
            str(python_path),
            str(script_path),
            "--qdpx",
            str(qdpx_path),
            *passthrough,
        ]
    command = " ".join(f'"{p}"' if " " in p else p for p in parts)
    return f'Set-Location -LiteralPath "{workspace_root}"; {command}'


def _launch_in_new_window(command: str, powershell_command: str, workspace_root: Path) -> bool:
    launch_attempts: list[list[str]] = []

    if os.name == "nt":
        if shutil.which("pwsh"):
            launch_attempts.append(
                [
                    "pwsh",
                    "-NoProfile",
                    "-Command",
                    f'Start-Process pwsh -ArgumentList "-NoExit","-Command","{powershell_command}"',
                ]
            )
        if shutil.which("powershell"):
            ps_start = (
                'Start-Process powershell '
                f'-ArgumentList "-NoExit","-Command","{powershell_command}"'
            )
            launch_attempts.append(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    ps_start,
                ]
            )

    if shutil.which("wt.exe"):
        launch_attempts.append(
            [
                "wt.exe",
                "new-tab",
                "wsl.exe",
                "--cd",
                str(workspace_root),
                "bash",
                "-lc",
                command,
            ]
        )

    if shutil.which("x-terminal-emulator"):
        launch_attempts.append(
            ["x-terminal-emulator", "-e", "bash", "-lc", f"{command}; exec bash"]
        )

    if shutil.which("gnome-terminal"):
        launch_attempts.append(["gnome-terminal", "--", "bash", "-lc", f"{command}; exec bash"])

    if shutil.which("konsole"):
        launch_attempts.append(["konsole", "-e", "bash", "-lc", f"{command}; exec bash"])

    if shutil.which("xfce4-terminal"):
        launch_attempts.append(
            ["xfce4-terminal", "--hold", "-e", f"bash -lc {shlex.quote(command)}"]
        )

    if shutil.which("xterm"):
        launch_attempts.append(["xterm", "-hold", "-e", "bash", "-lc", command])

    for args in launch_attempts:
        try:
            subprocess.Popen(args)
            return True
        except OSError:
            continue
    return False


def _run_in_current_terminal(workspace_root: Path, qdpx_path: Path, passthrough: list[str]) -> int:
    poetry_path = _resolve_poetry_path()
    if poetry_path:
        cmd = [poetry_path, "run", "qdpx-dedupe", "--qdpx", str(qdpx_path), *passthrough]
        return subprocess.call(cmd, cwd=workspace_root)

    script_path = workspace_root / "thesis_cli" / "qdpx_dedupe_tui.py"
    cmd = [sys.executable, str(script_path), "--qdpx", str(qdpx_path), *passthrough]
    return subprocess.call(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch QDPX dedupe TUI (current terminal by default)."
    )
    parser.add_argument(
        "--qdpx",
        type=Path,
        default=None,
        help="Path to .qdpx file (defaults to newest in ./qdpx or root).",
    )
    parser.add_argument(
        "--new-window",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Launch in a new terminal window/tab (default: false).",
    )
    args, passthrough = parser.parse_known_args()

    workspace_root = Path(__file__).resolve().parent.parent
    qdpx_path = (
        args.qdpx.resolve()
        if args.qdpx
        else _pick_qdpx_interactive(_find_qdpx_candidates(workspace_root), workspace_root)
    )

    if not qdpx_path.exists():
        print(f"QDPX not found: {qdpx_path}", file=sys.stderr)
        return 2

    poetry_path = _resolve_poetry_path()
    inner = _build_inner_command(workspace_root, qdpx_path, passthrough, poetry_path)
    ps_inner = _build_powershell_command(workspace_root, qdpx_path, passthrough, poetry_path)

    if args.new_window:
        if _launch_in_new_window(inner, ps_inner, workspace_root):
            print("Launched QDPX dedupe TUI in a new terminal window.")
            return 0
        print("No supported terminal launcher found. Running TUI in current terminal.")

    return _run_in_current_terminal(workspace_root, qdpx_path, passthrough)


if __name__ == "__main__":
    raise SystemExit(main())
