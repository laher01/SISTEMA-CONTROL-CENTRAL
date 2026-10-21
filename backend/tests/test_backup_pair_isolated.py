"""Pruebas del coordinador offline; nunca necesitan PostgreSQL ni VPS."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
sys.path.insert(0, str(DEPLOY))
spec = importlib.util.spec_from_file_location(
    "backup_pair_isolated", DEPLOY / "backup_pair_isolated.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_solo_bases_de_laboratorio():
    with pytest.raises(ValueError):
        mod.conexion("factcentral", "postgres")
    with pytest.raises(ValueError):
        mod.conexion("factcentral_recovery_prueba", "postgres")
    with pytest.raises(ValueError):
        mod.conexion("factcentral_fixture_test", "postgres;rm")
    assert mod.conexion("factcentral_fixture_test", "operador")[0:2] == ["-h", "127.0.0.1"]
    assert mod.conexion("factcentral_recovery_test", "operador", True)


def test_manifiesto_desde_base_restaurada():
    tenant = "4e24e14a-e96b-4c50-97aa-b233c70b9b11"
    contenido = b"documento ficticio"
    sha = hashlib.sha256(contenido).hexdigest()
    ruta = f"{tenant}/{sha[:2]}/{sha}"
    with patch.object(
        mod, "ejecutar", side_effect=[b"1\n", f"{tenant}\t{ruta}\t{sha}\n".encode()]
    ) as comando:
        filas = mod.manifest_desde_restaurada("factcentral_recovery_test", "operador")
    assert filas == [[tenant, ruta, sha]]
    assert all("factcentral_recovery_test" in str(c) for c in comando.call_args_list)


def test_manifiesto_rechaza_rutas_cruzadas_y_recuento():
    tenant = "4e24e14a-e96b-4c50-97aa-b233c70b9b11"
    sha = "a" * 64
    with (
        patch.object(
            mod, "ejecutar", side_effect=[b"1\n", f"{tenant}\t../../otro/{sha}\t{sha}\n".encode()]
        ),
        pytest.raises(ValueError, match="canónica"),
    ):
        mod.manifest_desde_restaurada("factcentral_recovery_test", "operador")
    with (
        patch.object(mod, "ejecutar", side_effect=[b"2\n", b""]),
        pytest.raises(ValueError, match="Recuento"),
    ):
        mod.manifest_desde_restaurada("factcentral_recovery_test", "operador")


def test_no_restaurar_sobre_base_con_tablas(tmp_path):
    pareja = tmp_path / "pareja.json"
    pareja.write_text("{}")
    with (
        patch.object(mod, "_leer_par", return_value=(tmp_path / "p", tmp_path / "t", "a" * 64)),
        patch.object(mod, "ejecutar", return_value=b"1\n") as ejecutar,
        pytest.raises(ValueError, match="vacía"),
    ):
        mod.probar(pareja, "factcentral_recovery_test", "operador", tmp_path / "nuevo")
    assert ejecutar.call_count == 1


def test_rechaza_par_corrupto_y_rutas_modificadas(tmp_path):
    dump = tmp_path / "postgres.dump"
    tar = tmp_path / "documentos.tar"
    dump.write_bytes(b"postgres ficticio")
    tar.write_bytes(b"tar ficticio")
    registro = {
        "formato": 1,
        "consistencia": "QUIESCENCIA_EXTERNA_NO_VERIFICADA",
        "postgres": {
            "archivo": "postgres.dump",
            "sha256": mod.huella(dump),
            "bytes": dump.stat().st_size,
        },
        "documentos": {
            "archivo": "documentos.tar",
            "sha256": mod.huella(tar),
            "bytes": tar.stat().st_size,
        },
    }
    pareja = tmp_path / "pareja.json"
    pareja.write_text(json.dumps(registro))
    assert mod._leer_par(pareja)[0] == dump
    tar.write_bytes(b"alterado")
    with pytest.raises(ValueError):
        mod._leer_par(pareja)
    registro["documentos"]["archivo"] = "../../otro"
    pareja.write_text(json.dumps(registro))
    with pytest.raises(ValueError):
        mod._leer_par(pareja)


def test_verificacion_falla_cerrada_ante_hash_incorrecto(tmp_path):
    tenant = "4e24e14a-e96b-4c50-97aa-b233c70b9b11"
    sha = hashlib.sha256(b"contenido original").hexdigest()
    filas = [[tenant, f"{tenant}/{sha[:2]}/{sha}", sha]]
    with (
        patch.object(mod, "_leer_par", return_value=(tmp_path / "db", tmp_path / "tar", sha)),
        patch.object(mod, "ejecutar", return_value=b"0\n"),
        patch.object(
            mod, "restaurar", side_effect=lambda _tar, destino, _sha: destino.mkdir()
        ) as restaura,
        patch.object(mod, "manifest_desde_restaurada", return_value=filas),
        pytest.raises(ValueError, match="verificación documental"),
    ):
        raiz = tmp_path / "restaurado"
        mod.probar(tmp_path / "pareja.json", "factcentral_recovery_test", "operador", raiz)
    restaura.assert_called_once()
