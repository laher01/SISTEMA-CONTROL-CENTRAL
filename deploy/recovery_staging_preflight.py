#!/usr/bin/env python3
"""Safe, offline-only preflight for an operator-run staging recovery.

This script intentionally does not connect to databases, hosts or volumes.
"""
import argparse
import pathlib
import sys


def verify(args):
    if args.confirm != "ISOLATED-STAGING-ONLY":
        raise ValueError("Missing operator confirmation")
    if args.source_env != "staging" or args.target_env != "ephemeral":
        raise ValueError("Only staging source and ephemeral target allowed")
    if args.source_database == args.target_database:
        raise ValueError("Source and target databases must differ")
    if not args.source_database.strip() or not args.target_database.strip():
        raise ValueError("Database identifiers required")
    source = pathlib.Path(args.source_documents)
    target = pathlib.Path(args.target_documents)
    if source.is_symlink() or target.is_symlink():
        raise ValueError("Symlink document root forbidden")
    if any(p.is_symlink() for p in (*source.parents, *target.parents)):
        raise ValueError("Symlink document parent forbidden")
    src = source.resolve(strict=True)
    dst = target.resolve(strict=True)
    if src == dst or src in dst.parents or dst in src.parents:
        raise ValueError("Document volumes overlap")
    if not dst.is_dir() or any(dst.iterdir()):
        raise ValueError("Target directory must be empty")
    if not args.expected_host.strip() or not args.actual_host.strip():
        raise ValueError("Host identifiers required")
    if args.expected_host != args.actual_host:
        raise ValueError("Host authorization mismatch")
    if not args.expected_host or args.expected_host.lower() in {"localhost", "production", "prod"}:
        raise ValueError("Untrusted staging host identifier")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--confirm", required=True)
    p.add_argument("--source-env", required=True)
    p.add_argument("--target-env", required=True)
    p.add_argument("--source-database", required=True)
    p.add_argument("--target-database", required=True)
    p.add_argument("--source-documents", required=True)
    p.add_argument("--target-documents", required=True)
    p.add_argument("--expected-host", required=True)
    p.add_argument("--actual-host", required=True)
    verify(p.parse_args())
    print("STAGING_RECOVERY_PREFLIGHT_OK")
    print("NO_REMOTE_ACTION_EXECUTED")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        print(f"STAGING_RECOVERY_PREFLIGHT_FAILED: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
