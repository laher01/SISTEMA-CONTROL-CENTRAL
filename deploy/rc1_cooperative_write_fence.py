#!/usr/bin/env python3
"""Barrera cooperativa offline para escritores de fixtures RC1.

Los escritores que NO adquieran el candado no son bloqueados: usar exclusivamente
con todos los escritores bajo este protocolo y un PostgreSQL aislado.
"""
import contextlib
import fcntl
import os
from pathlib import Path
from typing import Iterator


@contextlib.contextmanager
def candado(ruta: Path, *, exclusivo: bool, no_bloquear: bool = False) -> Iterator[None]:
    """Compartido para escribir, exclusivo durante la captura."""
    if ruta.is_symlink():
        raise ValueError("Candado simbólico prohibido")
    fd = os.open(ruta, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        modo = fcntl.LOCK_EX if exclusivo else fcntl.LOCK_SH
        if no_bloquear:
            modo |= fcntl.LOCK_NB
        fcntl.flock(fd, modo)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def escribir_fixture(candado_path: Path, destino: Path, bytes_doc: bytes) -> None:
    """Escritor adherido al protocolo; mantiene candado durante escritura."""
    with candado(candado_path, exclusivo=False):
        destino.write_bytes(bytes_doc)


def capturar_fixture(candado_path: Path, accion) -> None:
    """Solo captura cuando ningún escritor cooperativo mantiene candado."""
    with candado(candado_path, exclusivo=True):
        accion()
