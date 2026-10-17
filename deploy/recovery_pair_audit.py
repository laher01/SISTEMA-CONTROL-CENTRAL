#!/usr/bin/env python3
"""Offline recovery manifest auditor. Never connects to staging or production."""
import argparse
import hashlib
import json
import pathlib
import sys
import tarfile


def digest(stream):
    h = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        h.update(chunk)
    return h.hexdigest()


def relative_path(name):
    p = pathlib.PurePosixPath(name)
    if not name or name.startswith("/") or "\\" in name or any(
        part in ("", ".", "..") for part in name.split("/")
    ):
        raise ValueError("Unsafe archive path")
    if p.is_absolute():
        raise ValueError("Absolute archive path")
    return str(p)


def inspect_tar(path):
    entries = {}
    with tarfile.open(path, mode="r:gz") as archive:
        for item in archive:
            name = relative_path(item.name.removeprefix("./"))
            if item.isdir():
                continue
            if not item.isfile() or item.issym() or item.islnk():
                raise ValueError("Non-regular archive entry")
            if name in entries:
                raise ValueError("Duplicate archive path")
            f = archive.extractfile(item)
            if f is None:
                raise ValueError("Missing member")
            with f:
                entries[name] = {"size": item.size, "sha256": digest(f)}
    if not entries:
        raise ValueError("Empty archive")
    return entries


def compare(manifest, entries):
    expected = manifest["files"]
    if set(expected) != set(entries):
        raise ValueError("File inventory mismatch")
    for name, item in expected.items():
        if relative_path(name) != name:
            raise ValueError("Unsafe manifest path")
        if entries[name] != item:
            raise ValueError("File hash/size mismatch")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--dump", required=True)
    parser.add_argument("--batch", required=True)
    args = parser.parse_args()
    manifest = json.loads(pathlib.Path(args.manifest).read_text(encoding="utf-8"))
    if manifest.get("batch") != args.batch:
        raise ValueError("Unmatched backup batch")
    with open(args.dump, "rb") as database:
        if manifest.get("database_sha256") != digest(database):
            raise ValueError("Database hash mismatch")
    with open(args.archive, "rb") as documents:
        if manifest.get("archive_sha256") != digest(documents):
            raise ValueError("Archive hash mismatch")
    compare(manifest, inspect_tar(args.archive))
    print("BACKUP_PAIR_HASHES_AND_FILES_VERIFIED")
    print("NOT_A_DATABASE_RESTORE_OR_TENANT_RBAC_TEST")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, json.JSONDecodeError, tarfile.TarError) as error:
        print(f"RECOVERY_AUDIT_FAILED: {type(error).__name__}", file=sys.stderr)
        sys.exit(1)
