#!/usr/bin/env python3
"""Safely extract an immutable audited tar into an empty disposable directory."""
import argparse
import hashlib
import json
import pathlib
import sys
import tarfile

from recovery_pair_audit import compare, inspect_tar


def extract(archive_path, manifest_path, target):
    archive = pathlib.Path(archive_path)
    target = pathlib.Path(target)
    if target.is_symlink() or not target.is_dir() or any(target.iterdir()):
        raise ValueError("Target must be an empty non-symlink directory")
    if any(p.is_symlink() for p in target.parents):
        raise ValueError("Symlink in destination parents")
    manifest = json.loads(pathlib.Path(manifest_path).read_text())
    with archive.open("rb") as inp:
        archive_hash = hashlib.file_digest(inp, "sha256").hexdigest()
    if manifest["archive_sha256"] != archive_hash:
        raise ValueError("Archive checksum mismatch")
    entries = inspect_tar(archive)
    compare(manifest, entries)
    # Read from the same archived path after audit and re-verify each extracted byte.
    try:
        with tarfile.open(archive, "r:gz") as tf:
            for member in tf:
                if member.isdir():
                    continue
                name = member.name.removeprefix("./")
                expected = manifest["files"][name]
                dest = target.joinpath(*name.split("/"))
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists() or dest.is_symlink():
                    raise ValueError("Output conflict")
                content = tf.extractfile(member)
                if content is None:
                    raise ValueError("Missing archive file")
                total = 0
                h = hashlib.sha256()
                with content, dest.open("xb") as out:
                    while part := content.read(1048576):
                        total += len(part)
                        if total > expected["size"]:
                            raise ValueError("File length exceeded")
                        h.update(part)
                        out.write(part)
                if total != expected["size"] or h.hexdigest() != expected["sha256"]:
                    raise ValueError("Extracted file checksum mismatch")
    except Exception:
        # Caller owns cleanup of disposable directory; never promote partial contents.
        raise
    print("SAFE_SYNTHETIC_EXTRACTION_VERIFIED")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--archive", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--target", required=True)
    a = p.parse_args()
    try:
        extract(a.archive, a.manifest, a.target)
    except (ValueError, OSError, KeyError, tarfile.TarError) as e:
        print(f"SAFE_EXTRACT_FAILED: {type(e).__name__}", file=sys.stderr)
        sys.exit(1)
