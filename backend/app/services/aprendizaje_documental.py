from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CorreccionIA, Documento, Empresa, PerfilExtraccion


def aplicar_perfiles_aprendidos(
    session: Session,
    documento: Documento,
    procesamiento: dict[str, object],
) -> None:
    extraccion = procesamiento.get("extraccion_estructurada")
    if not isinstance(extraccion, dict):
        return

    formato = str(extraccion.get("formato_documental") or "DESCONOCIDO")
    documento.formato_origen = formato
    campos = extraccion.get("campos")
    if not isinstance(campos, dict):
        return

    for tipo_parte in ("emisor", "receptor"):
        ruc_dato = campos.get(f"ruc_{tipo_parte}")
        if not isinstance(ruc_dato, dict) or ruc_dato.get("valor") is None:
            continue
        ruc = str(ruc_dato["valor"])
        perfil = session.scalar(
            select(PerfilExtraccion).where(
                PerfilExtraccion.tenant_id == documento.tenant_id,
                PerfilExtraccion.ruc == ruc,
                PerfilExtraccion.tipo_parte == tipo_parte,
                PerfilExtraccion.formato == formato,
                PerfilExtraccion.activo.is_(True),
            )
        )
        if perfil is None:
            continue

        nombre = f"razon_social_{tipo_parte}"
        actual = campos.get(nombre)
        confianza_actual = 0.0
        if isinstance(actual, dict):
            try:
                confianza_actual = float(actual.get("confianza", 0))
            except (TypeError, ValueError):
                confianza_actual = 0.0
        if actual is None or confianza_actual < float(perfil.confianza):
            campos[nombre] = {
                "valor": perfil.razon_social,
                "confianza": float(perfil.confianza),
                "fuente": "PERFIL_APRENDIDO",
                "evidencia": f"Perfil {formato} para RUC {ruc}",
                "requiere_confirmacion": False,
            }
            perfil.usos += 1


def registrar_correccion_y_aprender(
    session: Session,
    documento: Documento,
    actor_codigo: str,
    actor_rol: str,
    campos_corregidos: dict[str, object],
    motivo: str | None = None,
) -> None:
    datos = documento.datos_extraidos or {}
    procesamiento = datos.get("procesamiento_documental")
    original: dict[str, object] | None = None
    formato = documento.formato_origen or "DESCONOCIDO"
    if isinstance(procesamiento, dict):
        extraccion = procesamiento.get("extraccion_estructurada")
        if isinstance(extraccion, dict):
            original = extraccion
            formato = str(extraccion.get("formato_documental") or formato)

    session.add(
        CorreccionIA(
            tenant_id=documento.tenant_id,
            documento_id=documento.id,
            actor_codigo=actor_codigo,
            actor_rol=actor_rol,
            formato=formato,
            resultado_original=original,
            resultado_corregido=dict(campos_corregidos),
            motivo=motivo,
        )
    )

    for tipo_parte in ("emisor", "receptor"):
        ruc = str(campos_corregidos.get(f"ruc_{tipo_parte}", "")).strip()
        razon = str(campos_corregidos.get(f"razon_social_{tipo_parte}", "")).strip()
        if len(ruc) != 11 or not ruc.isdigit() or not razon:
            continue

        perfil = session.scalar(
            select(PerfilExtraccion).where(
                PerfilExtraccion.tenant_id == documento.tenant_id,
                PerfilExtraccion.ruc == ruc,
                PerfilExtraccion.tipo_parte == tipo_parte,
                PerfilExtraccion.formato == formato,
            )
        )
        if perfil is None:
            perfil = PerfilExtraccion(
                tenant_id=documento.tenant_id,
                ruc=ruc,
                tipo_parte=tipo_parte,
                formato=formato,
                razon_social=razon[:300],
                confianza=Decimal("0.9900"),
                usos=0,
                activo=True,
            )
            session.add(perfil)
        else:
            perfil.razon_social = razon[:300]
            perfil.confianza = Decimal("0.9900")
            perfil.activo = True

        empresa = session.scalar(
            select(Empresa).where(
                Empresa.tenant_id == documento.tenant_id,
                Empresa.ruc == ruc,
                Empresa.deleted_at.is_(None),
            )
        )
        if empresa is not None:
            empresa.razon_social = razon[:300]
