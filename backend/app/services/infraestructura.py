import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Tenant
from app.models_infraestructura import (
    EventoInfraestructura,
    NodoInfraestructura,
    ReporteNodo,
    TenantNodo,
    VersionInfraestructura,
)
from app.repositories.infraestructura import InfraestructuraRepository
from app.schemas_infraestructura import NodoIn, ReporteIn, TenantNodoIn, VersionIn
from app.security import ContextoAcceso
from app.services import auditoria


def en_utc(fecha: datetime) -> datetime:
    return fecha.replace(tzinfo=UTC) if fecha.tzinfo is None else fecha.astimezone(UTC)


class InfraestructuraService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = InfraestructuraRepository(session)

    def obtener_nodo(self, nodo_id: uuid.UUID) -> NodoInfraestructura:
        nodo = self.repository.nodo(nodo_id)
        if nodo is None:
            raise HTTPException(404, "Nodo no encontrado")
        return nodo

    def registrar_evento(
        self,
        auth: ContextoAcceso,
        correlacion: uuid.UUID,
        accion: str,
        recurso_id: uuid.UUID,
        datos: dict[str, object] | None = None,
    ) -> None:
        datos = datos or {}
        self.session.add(
            EventoInfraestructura(
                actor_cuenta_id=auth.cuenta_id,
                correlacion_id=correlacion,
                accion=accion,
                recurso_id=recurso_id,
                resultado="EXITO",
                datos=datos,
            )
        )
        auditoria.registrar(
            self.session,
            auth.tenant_id,
            accion,
            "Infraestructura",
            recurso_id,
            {**datos, "actor": str(auth.cuenta_id), "correlacion": str(correlacion)},
        )

    def guardar(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise HTTPException(409, "El registro ya existe o entra en conflicto") from exc

    def crear_nodo(
        self, datos: NodoIn, auth: ContextoAcceso, correlacion: uuid.UUID
    ) -> NodoInfraestructura:
        nodo = NodoInfraestructura(id=uuid.uuid4(), **datos.model_dump())
        self.session.add(nodo)
        self.registrar_evento(auth, correlacion, "infra.nodo.creado", nodo.id)
        self.guardar()
        return nodo

    def actualizar_nodo(
        self,
        nodo_id: uuid.UUID,
        datos: NodoIn,
        auth: ContextoAcceso,
        correlacion: uuid.UUID,
    ) -> NodoInfraestructura:
        nodo = self.obtener_nodo(nodo_id)
        if not nodo.activo:
            raise HTTPException(409, "El nodo está desactivado")
        for campo, valor in datos.model_dump().items():
            setattr(nodo, campo, valor)
        self.registrar_evento(auth, correlacion, "infra.nodo.actualizado", nodo.id)
        self.guardar()
        return nodo

    def desactivar_nodo(
        self, nodo_id: uuid.UUID, auth: ContextoAcceso, correlacion: uuid.UUID
    ) -> None:
        nodo = self.obtener_nodo(nodo_id)
        if not nodo.activo:
            return
        nodo.activo = False
        nodo.token_hash = None
        self.registrar_evento(auth, correlacion, "infra.nodo.desactivado", nodo.id)
        self.guardar()

    def rotar_token(self, nodo_id: uuid.UUID, auth: ContextoAcceso, correlacion: uuid.UUID) -> str:
        nodo = self.obtener_nodo(nodo_id)
        if not nodo.activo:
            raise HTTPException(409, "El nodo está desactivado")
        token = secrets.token_urlsafe(48)
        nodo.token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.registrar_evento(auth, correlacion, "infra.nodo.credencial_rotada", nodo.id)
        self.guardar()
        return token

    def autenticar_agente(self, nodo_id: uuid.UUID, token: str) -> NodoInfraestructura:
        nodo = self.repository.nodo(nodo_id)
        recibido = hashlib.sha256(token.encode()).hexdigest()
        if (
            nodo is None
            or not nodo.activo
            or nodo.token_hash is None
            or not secrets.compare_digest(nodo.token_hash, recibido)
        ):
            raise HTTPException(401, "Credencial de agente inválida")
        return nodo

    def reportar(self, nodo: NodoInfraestructura, datos: ReporteIn) -> ReporteNodo:
        contenido = json.dumps(datos.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        huella = hashlib.sha256(contenido.encode()).hexdigest()
        previo = self.repository.reporte(nodo.id, datos.reporte_id)
        if previo:
            if previo.contenido_hash != huella:
                raise HTTPException(409, "La clave de reporte ya tiene otro contenido")
            return previo
        reporte = ReporteNodo(nodo_id=nodo.id, contenido_hash=huella, **datos.model_dump())
        self.session.add(reporte)
        nodo.ultima_conexion = datetime.now(UTC)
        nodo.version_instalada = datos.version
        self.guardar()
        return reporte

    def crear_version(
        self, datos: VersionIn, auth: ContextoAcceso, correlacion: uuid.UUID
    ) -> VersionInfraestructura:
        version = VersionInfraestructura(id=uuid.uuid4(), **datos.model_dump())
        self.session.add(version)
        self.registrar_evento(auth, correlacion, "infra.version.registrada", version.id)
        self.guardar()
        return version

    def asociar_tenant(
        self, datos: TenantNodoIn, auth: ContextoAcceso, correlacion: uuid.UUID
    ) -> TenantNodo:
        nodo = self.obtener_nodo(datos.nodo_id)
        if not nodo.activo:
            raise HTTPException(409, "El nodo está desactivado")
        if self.session.get(Tenant, datos.tenant_id) is None:
            raise HTTPException(404, "Tenant no encontrado")
        previo = self.session.scalar(
            select(TenantNodo).where(TenantNodo.tenant_id == datos.tenant_id)
        )
        if previo:
            if previo.nodo_id != nodo.id:
                raise HTTPException(
                    409, "El tenant ya está ubicado; una migración requiere otro flujo"
                )
            return previo
        asociacion = TenantNodo(id=uuid.uuid4(), **datos.model_dump())
        self.session.add(asociacion)
        self.registrar_evento(
            auth,
            correlacion,
            "infra.tenant.asociado",
            asociacion.id,
            {"tenant_id": str(datos.tenant_id), "nodo_id": str(nodo.id)},
        )
        self.guardar()
        return asociacion

    def resumen_nodo(self, nodo: NodoInfraestructura, settings: Settings) -> dict[str, object]:
        reporte = self.repository.ultimo_reporte(nodo.id)
        desconectado = (
            nodo.ultima_conexion is not None
            and (datetime.now(UTC) - en_utc(nodo.ultima_conexion)).total_seconds()
            > settings.infra_desconexion_segundos
        )
        estado = (
            "INACTIVO"
            if not nodo.activo
            else "DESCONECTADO"
            if desconectado
            else "CONECTADO"
            if reporte
            else "DESCONOCIDO"
        )
        alertas: list[str] = []
        if nodo.activo and desconectado:
            alertas.append("NODO_DESCONECTADO")
        if nodo.activo and reporte:
            for servicio, valor in reporte.servicios.items():
                if valor == "FALLO":
                    alertas.append(f"{servicio.upper()}_NO_DISPONIBLE")
            for recurso, valor, umbral in (
                ("CPU", reporte.cpu_porcentaje, settings.infra_cpu_umbral),
                ("RAM", reporte.ram_porcentaje, settings.infra_ram_umbral),
                ("DISCO", reporte.disco_porcentaje, settings.infra_disco_umbral),
            ):
                if valor is not None and valor >= umbral:
                    alertas.append(f"{recurso}_ELEVADO")
        return {
            "id": nodo.id,
            "codigo": nodo.codigo,
            "nombre": nodo.nombre,
            "hostname": nodo.hostname,
            "endpoint_privado": nodo.endpoint_privado,
            "proveedor": nodo.proveedor,
            "region": nodo.region,
            "sistema_operativo": nodo.sistema_operativo,
            "entorno": nodo.entorno,
            "activo": nodo.activo,
            "estado": estado,
            "cpu_nucleos": nodo.cpu_nucleos,
            "ram_bytes": nodo.ram_bytes,
            "disco_bytes": nodo.disco_bytes,
            "ultima_conexion": nodo.ultima_conexion,
            "ultimo_despliegue": nodo.ultimo_despliegue,
            "version_instalada": nodo.version_instalada,
            "cpu_porcentaje": reporte.cpu_porcentaje if reporte else None,
            "ram_porcentaje": reporte.ram_porcentaje if reporte else None,
            "disco_porcentaje": reporte.disco_porcentaje if reporte else None,
            "servicios": reporte.servicios if reporte else {},
            "metricas_vigentes": bool(reporte and nodo.activo and not desconectado),
            "tenants": [str(a.tenant_id) for a in self.repository.asociaciones(nodo.id)],
            "alertas": alertas,
        }

    def dashboard(self, settings: Settings) -> dict[str, object]:
        nodos = [self.resumen_nodo(n, settings) for n in self.repository.nodos()]
        total = self.session.scalar(select(func.count()).select_from(NodoInfraestructura)) or 0
        activos = (
            self.session.scalar(
                select(func.count())
                .select_from(NodoInfraestructura)
                .where(NodoInfraestructura.activo.is_(True))
            )
            or 0
        )
        return {
            "total": total,
            "activos": activos,
            "inactivos": total - activos,
            "nodos": nodos,
            "limite_nodos": 200,
            "alertas": [
                {"nodo_id": n["id"], "codigo": n["codigo"], "alertas": n["alertas"]}
                for n in nodos
                if n["alertas"]
            ],
        }
