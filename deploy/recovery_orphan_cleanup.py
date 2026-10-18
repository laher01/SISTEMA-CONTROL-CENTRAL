#!/usr/bin/env python3
"""Offline cleanup planner. Operates only on explicit synthetic-owned temp roots.

Never reads GitHub/VPS credentials and never deletes a database.
"""
import argparse
import json
import math
import os
import pathlib
import shutil
import sys
import time

MARKER = ".factcentral-synthetic-restore.json"


def cleanup(root, *, now, ttl, dry_run=True):
    if not isinstance(ttl, (int, float)) or not math.isfinite(ttl) or ttl < 3600:
        raise ValueError('Cleanup TTL must be at least 3600 seconds')
    if not isinstance(now, (int, float)) or not math.isfinite(now):
        raise ValueError('Invalid current timestamp')
    root = pathlib.Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Invalid cleanup root")
    removed = []
    for candidate in root.iterdir():
        if candidate.is_symlink() or not candidate.is_dir():
            continue
        marker = candidate / MARKER
        if marker.is_symlink() or not marker.is_file():
            continue
        data = json.loads(marker.read_text(encoding="utf-8"))
        if data.get("kind") != "factcentral-ci-ephemeral" or data.get("name") != candidate.name:
            continue
        pid = data.get("pid")
        # Do not act on PID-marked resources: reused PIDs cannot prove ownership.
        # A future authenticated lease/reconciler must decide their disposition.
        if pid is not None:
            continue
        if any(os.path.ismount(p) for p in (candidate, *candidate.rglob("*"))):
            continue
        if any(p.is_symlink() for p in candidate.rglob("*")):
            continue
        created = data.get("created_at")
        if type(created) not in (int, float) or not math.isfinite(created) or created > now or now - created < ttl:
            continue
        if not candidate.resolve().is_relative_to(root.resolve()):
            raise ValueError("Candidate escapes root")
        removed.append(candidate.name)
        if not dry_run:
            shutil.rmtree(candidate)
    return removed


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--ttl-seconds", type=int, default=3600)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    if args.ttl_seconds < 3600:
        raise ValueError("TTL too short")
    if args.apply:
        if sys.platform != "linux" or not pathlib.Path("/proc/self").exists():
            raise ValueError("Cleanup apply requires Linux")
        if not (os.environ.get("CI") == "true" and os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("FC_RECOVERY_SYNTHETIC_ONLY") == "YES"):
            raise ValueError("Cleanup apply restricted to synthetic GitHub Actions CI")
    print(json.dumps({"candidates": cleanup(args.root, now=time.time(), ttl=args.ttl_seconds,
                                           dry_run=not args.apply), "dry_run": not args.apply}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"EPHEMERAL_CLEANUP_FAILED: {type(e).__name__}", file=sys.stderr)
        sys.exit(1)
