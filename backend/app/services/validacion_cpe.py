"""Valida la identidad fiscal de una factura ingresada por un gestor."""

import re

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.enums import TipoDocumento
from app.models import ConfiguracionConsultasEmpresa, Documento, Expediente

URL_CPE = "https://api.apiperu.dev/cpe"


def validar_factura(
    session: Session, settings: Settings, expediente: Expediente, documento: Documento
) -> None:
    if documento.tipo_documento != TipoDocumento.FACT or documento.gestor_id is None:
        return
    consultar_factura(session, settings, expediente)


def consultar_factura(session: Session, settings: Settings, expediente: Expediente) -> str | None:
    ruc = expediente.emisor.ruc
    serie = expediente.serie.upper()
    numero = expediente.correlativo
    if (
        not re.fullmatch(r"[0-9]{11}", ruc)
        or not re.fullmatch(r"[A-Z0-9]{4}", serie)
        or not re.fullmatch(r"[0-9]+", numero)
        or not expediente.importe_total.is_finite()
        or expediente.importe_total < 0
    ):
        expediente.cpe_estado = "PENDIENTE"
        return None
    identidad = (
        f"{ruc}:{serie}:{int(numero)}:{expediente.fecha_emision}:{expediente.importe_total:.2f}"
    )
    if expediente.cpe_identidad == identidad and expediente.cpe_estado in {"VALIDO", "INVALIDO"}:
        return None
    expediente.cpe_estado = "PENDIENTE"
    expediente.cpe_identidad = identidad
    config = session.get(ConfiguracionConsultasEmpresa, expediente.tenant_id)
    token = (settings.consulta_coactiva_token or "").strip().strip("'\"").strip()
    if config is not None and config.token_cifrado:
        try:
            token = (
                Fernet(settings.consultas_empresas_encryption_key or "")
                .decrypt(config.token_cifrado.encode())
                .decode()
            )
        except (ValueError, InvalidToken):
            return "La credencial de APIPERU no se pudo leer."
    if not token:
        return "Configura la credencial de APIPERU antes de continuar."
    try:
        respuesta = httpx.post(
            URL_CPE,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            json={
                "ruc_emisor": ruc,
                "codigo_tipo_documento": "01",
                "serie_documento": serie,
                "numero_documento": str(int(numero)),
                "fecha_de_emision": expediente.fecha_emision.isoformat(),
                "total": float(expediente.importe_total),
            },
            timeout=5,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
    except httpx.HTTPStatusError as exc:
        estado_http = exc.response.status_code
        if estado_http in {401, 402, 403, 429} or estado_http >= 500:
            return f"APIPERU devolvió HTTP {estado_http}. La verificación se pausó."
        return None
    except httpx.RequestError:
        return "No hay conexión con APIPERU. La verificación se pausó."
    except ValueError:
        return None
    if not isinstance(datos, dict) or datos.get("success") is not True:
        return None
    comprobante = datos.get("data")
    if not isinstance(comprobante, dict):
        return None
    if (
        comprobante.get("ruc_emisor") != ruc
        or comprobante.get("serie_documento") != serie
        or str(comprobante.get("numero_documento", "")).lstrip("0") != numero.lstrip("0")
    ):
        return None
    if str(comprobante.get("comprobante_estado_codigo")) == "1":
        expediente.cpe_estado = "VALIDO"
        return None
    estado = str(comprobante.get("comprobante_estado_descripcion", "")).strip().upper()
    if estado in {"NO EXISTE", "ANULADO", "NO AUTORIZADO", "NO ACEPTADO", "RECHAZADO"}:
        expediente.cpe_estado = "INVALIDO"
    return None
