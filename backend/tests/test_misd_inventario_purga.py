"""Invariantes del inventario MISD antes de habilitar cualquier purga.

Estas pruebas no borran registros ni archivos. Usan metadatos del ORM y
escenarios sintéticos para detectar dependencias que el planificador deberá tratar.
"""

from app.models import Base


def _referencias_a(tabla_destino: str) -> set[tuple[str, str]]:
    return {
        (tabla.name, columna.name)
        for tabla in Base.metadata.tables.values()
        for columna in tabla.columns
        for clave in columna.foreign_keys
        if clave.column.table.name == tabla_destino
    }


def test_misd_inventario_expediente_exige_dependencias() -> None:
    referencias = _referencias_a("expedientes")
    assert ("documentos", "expediente_id") in referencias
    assert ("alertas", "expediente_id") in referencias
    assert ("referencias_gre", "expediente_id") in referencias
    assert ("solicitudes_retiro_misd", "expediente_id") in referencias


def test_misd_inventario_documento_exige_revisar_relaciones_y_pagos() -> None:
    referencias = _referencias_a("documentos")
    assert ("relaciones_documentos", "origen_id") in referencias
    assert ("relaciones_documentos", "destino_id") in referencias
    assert ("referencias_gre", "documento_id") in referencias
    assert ("correcciones_ia", "documento_id") in referencias
    assert ("pagos_erp", "voucher_documento_id") in referencias


def test_misd_storage_y_bloqueo_pago_siguen_presentes() -> None:
    documentos = Base.metadata.tables["documentos"]
    assert "tenant_id" in documentos.c
    assert "ruta_storage" in documentos.c
    assert "deleted_at" in documentos.c
    pagos = Base.metadata.tables["pagos_erp"]
    assert "tenant_id" in pagos.c
    assert "voucher_documento_id" in pagos.c


def test_misd_borrado_fisico_permanece_deshabilitado_en_api() -> None:
    from inspect import getsource

    from app.api.routes.documentos import capacidades_documentales

    fuente = getsource(capacidades_documentales)
    assert '"puede_eliminar_definitivamente": False' in fuente


def test_misd_politica_sintetica_bloquea_retiro_con_pago() -> None:
    from datetime import datetime, timezone
    from types import SimpleNamespace

    from app.services.misd_autorizaciones import politica_retiro

    instante = datetime.now(timezone.utc)
    expediente_sintetico = SimpleNamespace(created_at=instante)
    bloqueada = politica_retiro(expediente_sintetico, "GESTOR", instante, True)
    assert bloqueada["puede_solicitar"] is False
    assert bloqueada["requiere_aprobacion"] is False
    assert bloqueada["bloqueado_por_pago"] is True


def test_misd_politica_sintetica_distingue_ventana_y_aprobacion() -> None:
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace

    from app.services.misd_autorizaciones import politica_retiro

    instante = datetime.now(timezone.utc)
    expediente_sintetico = SimpleNamespace(created_at=instante - timedelta(minutes=31))
    revision = politica_retiro(expediente_sintetico, "GESTOR", instante, False)
    assert revision["puede_solicitar"] is True
    assert revision["requiere_aprobacion"] is True
    assert "RESPONSABLE" in revision["roles_aprobadores"]
    sin_permiso = politica_retiro(expediente_sintetico, "SECRETARIA", instante, False)
    assert sin_permiso["puede_solicitar"] is False
