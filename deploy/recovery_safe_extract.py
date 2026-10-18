#!/usr/bin/env python3
"""Safely extract an immutable audited tar into an empty disposable directory."""
import argparse
import hashlib
import json
import os
import tempfile
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
    # Freeze a private copy so subsequent reads cannot follow a mutable source path.
    with tempfile.TemporaryDirectory(prefix='fc-audit-') as private:
        frozen = pathlib.Path(private) / 'backup.tar.gz'
        with archive.open('rb') as source, frozen.open('xb') as dest:
            copied = 0
            while part := source.read(1048576):
                copied += len(part)
                if copied > 2 * 1024 * 1024 * 1024:
                    raise ValueError('Compressed archive size exceeded')
                dest.write(part)
        with frozen.open('rb') as source:
            if hashlib.file_digest(source, 'sha256').hexdigest() != archive_hash:
                raise ValueError('Backup changed during inspection')
        return _extract_frozen(frozen, manifest, target)


def _extract_frozen(archive, manifest, target):
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
                if any(p.is_symlink() for p in (dest.parent, *dest.parent.parents)):
                    raise ValueError('Symlink in extracted destination')
                if dest.exists() or dest.is_symlink():
                    raise ValueError("Output conflict")
                content = tf.extractfile(member)
                if content is None:
                    raise ValueError("Missing archive file")
                total = 0
                h = hashlib.sha256()
                with content, os.fdopen(os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600), "wb") as out:
                    while part := content.read(1048576):
                        total += len(part)
                        if total > expected["size"]:
                            raise ValueError("File length exceeded")
                        h.update(part)
                        out.write(part)
                if total != expected["size"] or h.hexdigest() != expected["sha256"]:
                    raise ValueError("Extracted file checksum mismatch")
    except Exception:
        # On failure remove only generated contents inside the disposable target.
        for candidate in sorted(target.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            if candidate.is_symlink() or candidate.is_file():
                candidate.unlink()
            elif candidate.is_dir():
                candidate.rmdir()
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
