#!/usr/bin/env python3
"""Rebuild the forwarding descriptor from an explicitly reviewed upstream commit."""

import argparse
import re
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("revision")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", args.revision):
        parser.error("set TEMPORAL_API_REVISION to a reviewed full upstream commit SHA")
    destination = Path(__file__).resolve().parents[1] / "temporal" / "descriptor.binpb"
    with tempfile.TemporaryDirectory(prefix="temporal-descriptor-") as temporary:
        checkout = Path(temporary)
        subprocess.run(["git", "init", "--quiet", str(checkout)], check=True)
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/temporalio/api.git"],
            cwd=checkout,
            check=True,
        )
        subprocess.run(
            ["git", "fetch", "--depth=1", "origin", args.revision],
            cwd=checkout,
            check=True,
        )
        subprocess.run(
            ["git", "checkout", "--detach", "FETCH_HEAD"], cwd=checkout, check=True
        )
        actual = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=checkout, text=True
        ).strip()
        if actual.lower() != args.revision.lower():
            raise SystemExit("upstream checkout does not match the requested commit")
        graph = checkout / "descriptor.binpb"
        subprocess.run(
            ["buf", "build", "--as-file-descriptor-set", "-o", str(graph)],
            cwd=checkout,
            check=True,
        )
        destination.write_bytes(graph.read_bytes())


if __name__ == "__main__":
    main()
