#!/usr/bin/env python3
"""Run repository adapter checks with live-provider opt-ins absent."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_NAMES = {
    "PATH",
    "HOME",
    "LD_LIBRARY_PATH",
    "LIBSTDCPP_DIR",
    "UV_PYTHON",
    "UV_CACHE_DIR",
    "UV_LINK_MODE",
    "TMPDIR",
    "SSL_CERT_FILE",
    "LANG",
    "LC_ALL",
    "GOTOOLCHAIN",
    "GOENV",
    "GOPATH",
    "GOCACHE",
    "GOMODCACHE",
}
GENERATED = "gen,*_pb2.py,*_pb2.pyi,*_pb2_grpc.py"
SCRIPTS = [
    "scripts/generate-go-adapters",
    "scripts/generate-python-adapters",
    "scripts/check-python-wiring.py",
    "scripts/check-adapters.py",
    "scripts/refresh-temporal-descriptor.py",
]


def run(command: list[str], directory: Path, environment: dict[str, str]) -> bool:
    print(f"{directory.name}: {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=directory, env=environment, check=False)
    print(
        f"{'PASS' if result.returncode == 0 else 'FAIL'}: {directory.name}", flush=True
    )
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "test-go",
            "test-py",
            "lint-go",
            "lint-py",
            "fmt",
            "audit-go",
            "audit-py",
        ],
    )
    args = parser.parse_args()
    environment = {name: os.environ[name] for name in ENV_NAMES if name in os.environ}
    go_modules = sorted(path.parent for path in ROOT.glob("*/go.mod"))
    py_modules = sorted(path.parent for path in ROOT.glob("*/pyproject.toml"))
    passed = True
    if args.action in {"lint-py", "fmt"}:
        commands = [
            ["ruff", "format", *([] if args.action == "fmt" else ["--check"]), *SCRIPTS]
        ]
        if args.action == "lint-py":
            commands.append(["ruff", "check", "--select", "E,F,I", *SCRIPTS])
        for command in commands:
            passed &= run(command, ROOT, environment)
    if args.action in {"test-go", "lint-go", "fmt", "audit-go"}:
        for directory in go_modules:
            if args.action == "lint-go":
                files = sorted(
                    str(path)
                    for path in directory.rglob("*.go")
                    if not any(
                        part.startswith(".")
                        for part in path.relative_to(directory).parts
                    )
                )
                formatted = subprocess.run(
                    ["gofmt", "-l", *files],
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if formatted.stdout:
                    print(formatted.stdout, end="")
                    passed = False
                commands = [["go", "vet", "./..."]]
            elif args.action == "test-go":
                commands = [["go", "test", "-count=1", "./..."]]
            elif args.action == "audit-go":
                commands = [["go", "mod", "verify"], ["govulncheck", "-test", "./..."]]
            else:
                commands = [["gofmt", "-w", "."]]
            for command in commands:
                passed &= run(command, directory, environment)
    if args.action in {"test-py", "lint-py", "fmt", "audit-py"}:
        for directory in py_modules:
            paths = [
                name
                for name in ["src", "main.py", "bindings.py", "tests"]
                if (directory / name).exists()
            ]
            if args.action == "test-py":
                if not (directory / "tests").exists() or not list(
                    (directory / "tests").glob("test_*.py")
                ):
                    continue
                commands = [
                    [
                        "uv",
                        "run",
                        "--locked",
                        "python",
                        "-m",
                        "pytest",
                        "tests/",
                        "-q",
                        "--no-header",
                    ]
                ]
            elif args.action == "audit-py":
                commands = [
                    ["uv", "run", "--locked", "--with", "pip-audit", "pip-audit"]
                ]
            elif args.action == "lint-py":
                commands = [
                    [
                        "uv",
                        "run",
                        "--locked",
                        "ruff",
                        "check",
                        "--exclude",
                        GENERATED,
                        *paths,
                    ],
                    [
                        "uv",
                        "run",
                        "--locked",
                        "ruff",
                        "format",
                        "--check",
                        "--exclude",
                        GENERATED,
                        *paths,
                    ],
                ]
            else:
                commands = [
                    [
                        "uv",
                        "run",
                        "--locked",
                        "ruff",
                        "format",
                        "--exclude",
                        GENERATED,
                        *paths,
                    ]
                ]
            for command in commands:
                passed &= run(command, directory, environment)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
