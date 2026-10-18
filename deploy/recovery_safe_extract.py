#!/usr/bin/env python3
"""Synthetic TAR recovery: descriptor-relative extraction, never remote staging."""
import argparse
import hashlib
import json
import os
import pathlib
import sys
import tarfile
import tempfile

from recovery_pair_audit import compare, inspect_tar, relative_path

MAX_COMPRESSED = 2 * 1024 * 1024 * 1024
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW


def _open_directory(root_fd, parts, created_dirs):
    fd = os.dup(root_fd)
    try:
        path = []
        for part in parts:
            path.append(part)
            try:
                os.mkdir(part, 0o700, dir_fd=fd)
                created_dirs.append(tuple(path))
            except FileExistsError:
                pass
            next_fd = os.open(part, DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def _rollback(root_fd, created_files, created_dirs):
    for parts in reversed(created_files):
        fd = _open_directory(root_fd, parts[:-1], [])
        try:
            os.unlink(parts[-1], dir_fd=fd)
        finally:
            os.close(fd)
    for parts in sorted(set(created_dirs), key=len, reverse=True):
        fd = _open_directory(root_fd, parts[:-1], [])
        try:
            os.rmdir(parts[-1], dir_fd=fd)
        finally:
            os.close(fd)


def extract(archive_path, manifest_path, target):
    root = pathlib.Path(target)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Target must be an empty non-symlink directory")
    if any(p.is_symlink() for p in root.parents):
        raise ValueError("Symlink parent forbidden")
    manifest = json.loads(pathlib.Path(manifest_path).read_text(encoding="utf-8"))
    # Freeze source before inspect/extract; reject concurrent mutation by digest.
    with tempfile.TemporaryDirectory(prefix="fc-audit-") as private:
        frozen = pathlib.Path(private) / "backup.tar.gz"
        with open(archive_path, "rb") as src, frozen.open("xb") as dst:
            count = 0
            h = hashlib.sha256()
            while chunk := src.read(1048576):
                count += len(chunk)
                if count > MAX_COMPRESSED:
                    raise ValueError("Compressed archive too large")
                h.update(chunk)
                dst.write(chunk)
        if h.hexdigest() != manifest["archive_sha256"]:
            raise ValueError("Archive hash mismatch")
        compare(manifest, inspect_tar(frozen))
        root_fd = os.open(root, DIR_FLAGS)
        created_files, created_dirs = [], []
        try:
            if os.listdir(root_fd):
                raise ValueError("Destination not empty")
            with tarfile.open(frozen, "r:gz") as archive:
                for member in archive:
                    name = relative_path(member.name.removeprefix("./"))
                    if member.isdir():
                        continue
                    if not member.isfile() or member.issym() or member.islnk():
                        raise ValueError("Unsafe archive member")
                    expected = manifest["files"][name]
                    parts = tuple(name.split("/"))
                    parent_fd = _open_directory(root_fd, parts[:-1], created_dirs)
                    try:
                        source = archive.extractfile(member)
                        if source is None:
                            raise ValueError("Missing file payload")
                        fd = os.open(parts[-1], FILE_FLAGS, 0o600, dir_fd=parent_fd)
                        created_files.append(parts)
                        total = 0
                        digest = hashlib.sha256()
                        with source, os.fdopen(fd, "wb") as out:
                            while chunk := source.read(1048576):
                                total += len(chunk)
                                if total > expected["size"]:
                                    raise ValueError("Extracted file exceeds expected length")
                                out.write(chunk)
                                digest.update(chunk)
                        if total != expected["size"] or digest.hexdigest() != expected["sha256"]:
                            raise ValueError("Extracted file digest mismatch")
                    finally:
                        os.close(parent_fd)
        except BaseException:
            _rollback(root_fd, created_files, created_dirs)
            raise
        finally:
            os.close(root_fd)
    print("SAFE_SYNTHETIC_EXTRACTION_VERIFIED")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--archive", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--target", required=True)
    args = p.parse_args()
    try:
        extract(args.archive, args.manifest, args.target)
    except (ValueError, OSError, KeyError, tarfile.TarError) as exc:
        print(f"SAFE_EXTRACT_FAILED: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
