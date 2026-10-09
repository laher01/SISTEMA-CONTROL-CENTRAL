import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models_infraestructura import (
    EventoInfraestructura,
    NodoInfraestructura,
    VersionInfraestructura,
)
from app.models_operaciones_infra import BackupInfra, OperacionInfra
from app.schemas_operaciones_infra import (
    BackupIn,
    DespliegueIn,
    LoteIn,
    ResultadoOperacionIn,
)
from app.security import ContextoAcceso
from app.services.infraestructura import InfraestructuraService, en_utc


class OperacionesInfraService(InfraestructuraService):
    def __init__(self, session: Session, settings: Settings) -> None:
        super().__init__(session)
        self.settings = settings

    def habilitar(self, nodo: NodoInfraestructura) -> None:
        if not self.settings.infra_operaciones_habilitadas:
            raise HTTPException(409, "La ejecución de infraestructura está deshabilitada")
        if nodo.entorno == "production" and not self.settings.infra_produccion_habilitada:
            raise HTTPException(409, "La ejecución productiva requiere habilitación explícita")
        if not nodo.activo:
            raise HTTPException(409, "El nodo está desactivado")

    def version(self, version_id: uuid.UUID) -> VersionInfraestructura:
        version = self.session.get(VersionInfraestructura, version_id)
        if version is None:
            raise HTTPException(404, "Versión no encontrada")
        return version

    def aprobar_version(
        self,
        version_id: uuid.UUID,
        evidencia: str,
        auth: ContextoAcceso,
        correlacion: uuid.UUID,
    ) -> VersionInfraestructura:
        version = self.version(version_id)
        if not version.imagen_frontend or not version.digest_frontend:
            raise HTTPException(409, "Debe registrar también la imagen frontend por digest")
        version.validacion = "VALIDADA"
        version.aprobacion = "APROBADA"
        self.registrar_evento(
            auth,
            correlacion,
            "infra.version.aprobada",
            version.id,
            {"evidencia_ci": evidencia, "validacion": "DECLARACION_SUPERADMIN"},
        )
        self.guardar()
        return version

    def preparar_despliegue(self, datos: DespliegueIn, tipo: str) -> dict[str, object]:
        nodo = self.obtener_nodo(datos.nodo_id)
        self.habilitar(nodo)
        version = self.version(datos.version_id)
        if version.validacion != "VALIDADA" or version.aprobacion != "APROBADA":
            raise HTTPException(409, "Versión sin validación y aprobación")
        if not version.imagen_frontend or not version.digest_frontend:
            raise HTTPException(409, "Versión sin imagen frontend por digest")
        if version.entorno != nodo.entorno:
            raise HTTPException(409, "El entorno de la versión no coincide con el nodo")
        if (
            not nodo.ultima_conexion
            or (datetime.now(UTC) - en_utc(nodo.ultima_conexion)).total_seconds()
            > self.settings.infra_desconexion_segundos
        ):
            raise HTTPException(409, "El nodo no tiene reporte reciente")
        if not nodo.migracion_instalada:
            raise HTTPException(409, "No se conoce la migración instalada")
        if tipo == "ROLLBACK_IMAGEN":
            if version.migracion_hasta != nodo.migracion_instalada:
                raise HTTPException(
                    409, "Rollback bloqueado: requiere recuperar datos o migraciones"
                )
        elif version.migracion_desde != nodo.migracion_instalada:
            raise HTTPException(409, "Migración de origen incompatible")
        if version.migracion_hasta != nodo.migracion_instalada:
            backup = self.session.get(BackupInfra, datos.backup_id) if datos.backup_id else None
            if (
                backup is None
                or backup.nodo_id != nodo.id
                or backup.estado != "VERIFICADO"
                or backup.migracion != nodo.migracion_instalada
                or backup.restauracion_verificada_at is None
                or (datetime.now(UTC) - en_utc(backup.created_at)).total_seconds() > 86400
            ):
                raise HTTPException(
                    409, "Se exige backup reciente con restauración aislada verificada"
                )
        return {
            "version_anterior": nodo.version_instalada,
            "migracion_anterior": nodo.migracion_instalada,
            "version": version.version,
            "migracion": version.migracion_hasta,
            "backend": f"{version.imagen_docker}@{version.digest}",
            "frontend": f"{version.imagen_frontend}@{version.digest_frontend}",
            "backup_id": str(datos.backup_id) if datos.backup_id else None,
        }

    def crear_operacion(
        self,
        nodo_id: uuid.UUID,
        solicitud_id: uuid.UUID,
        tipo: str,
        parametros: dict[str, object],
        auth: ContextoAcceso,
        correlacion: uuid.UUID,
        version_id: uuid.UUID | None = None,
        grupo_id: uuid.UUID | None = None,
        orden: int = 0,
    ) -> OperacionInfra:
        serializado = json.dumps(
            {"tipo": tipo, "version_id": str(version_id), "parametros": parametros},
            sort_keys=True,
            separators=(",", ":"),
        )
        huella = hashlib.sha256(serializado.encode()).hexdigest()
        previo = self.session.scalar(
            select(OperacionInfra).where(
                OperacionInfra.nodo_id == nodo_id,
                OperacionInfra.solicitud_id == solicitud_id,
            )
        )
        if previo:
            if previo.contenido_hash != huella:
                raise HTTPException(409, "Solicitud duplicada con otro contenido")
            return previo
        operacion = OperacionInfra(
            id=uuid.uuid4(),
            nodo_id=nodo_id,
            solicitud_id=solicitud_id,
            version_id=version_id,
            actor_cuenta_id=auth.cuenta_id,
            tipo=tipo,
            parametros=parametros,
            contenido_hash=huella,
            grupo_id=grupo_id,
            orden=orden,
        )
        self.session.add(operacion)
        self.registrar_evento(
            auth,
            correlacion,
            "infra.operacion.solicitada",
            operacion.id,
            {"tipo": tipo, "nodo_id": str(nodo_id), "version_id": str(version_id)},
        )
        return operacion

    def solicitar_despliegue(
        self,
        datos: DespliegueIn,
        auth: ContextoAcceso,
        correlacion: uuid.UUID,
        tipo: str = "DESPLIEGUE",
    ) -> OperacionInfra:
        # El fingerprint conserva la versión anterior de la primera solicitud al repetirla.
        previo = self.session.scalar(
            select(OperacionInfra).where(
                OperacionInfra.nodo_id == datos.nodo_id,
                OperacionInfra.solicitud_id == datos.solicitud_id,
            )
        )
        if previo:
            if (
                previo.tipo != tipo
                or previo.version_id != datos.version_id
                or previo.parametros.get("backup_id")
                != (str(datos.backup_id) if datos.backup_id else None)
            ):
                raise HTTPException(409, "Solicitud duplicada con otro contenido")
            return previo
        parametros = self.preparar_despliegue(datos, tipo)
        operacion = self.crear_operacion(
            datos.nodo_id,
            datos.solicitud_id,
            tipo,
            parametros,
            auth,
            correlacion,
            version_id=datos.version_id,
        )
        self.guardar()
        return operacion

    def solicitar_backup(
        self,
        datos: BackupIn,
        auth: ContextoAcceso,
        correlacion: uuid.UUID,
    ) -> OperacionInfra:
        nodo = self.obtener_nodo(datos.nodo_id)
        self.habilitar(nodo)
        operacion = self.crear_operacion(
            nodo.id,
            datos.solicitud_id,
            "BACKUP",
            {"retencion_dias": datos.retencion_dias},
            auth,
            correlacion,
        )
        self.guardar()
        return operacion

    def solicitar_lote(
        self,
        datos: LoteIn,
        auth: ContextoAcceso,
        correlacion: uuid.UUID,
    ) -> list[OperacionInfra]:
        if len(set(datos.nodos)) != len(datos.nodos):
            raise HTTPException(422, "No se puede repetir un nodo en el lote")
        previos = list(
            self.session.scalars(
                select(OperacionInfra)
                .where(
                    OperacionInfra.grupo_id == datos.solicitud_id,
                )
                .order_by(OperacionInfra.orden)
            )
        )
        if previos:
            if [o.nodo_id for o in previos] != datos.nodos or any(
                o.version_id != datos.version_id
                or o.parametros.get("backup_id")
                != (str(datos.backups[o.nodo_id]) if o.nodo_id in datos.backups else None)
                for o in previos
            ):
                raise HTTPException(409, "El lote ya existe con otro contenido")
            return previos
        preparados = [
            self.preparar_despliegue(
                DespliegueIn(
                    solicitud_id=uuid.uuid5(datos.solicitud_id, str(nodo)),
                    nodo_id=nodo,
                    version_id=datos.version_id,
                    backup_id=datos.backups.get(nodo),
                ),
                "DESPLIEGUE",
            )
            for nodo in datos.nodos
        ]
        operaciones = [
            self.crear_operacion(
                nodo,
                uuid.uuid5(datos.solicitud_id, str(nodo)),
                "DESPLIEGUE",
                parametros,
                auth,
                correlacion,
                version_id=datos.version_id,
                grupo_id=datos.solicitud_id,
                orden=orden,
            )
            for orden, (nodo, parametros) in enumerate(zip(datos.nodos, preparados, strict=True))
        ]
        self.guardar()
        return operaciones

    def reclamar(self, nodo: NodoInfraestructura) -> dict[str, object] | None:
        self.habilitar(nodo)
        hash_admitido = nodo.token_hash
        # Bloqueo por nodo: PostgreSQL serializa trabajadores concurrentes de un mismo agente.
        bloqueado = self.session.scalar(
            select(NodoInfraestructura)
            .where(
                NodoInfraestructura.id == nodo.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if bloqueado is None or bloqueado.token_hash != hash_admitido:
            raise HTTPException(401, "La credencial fue revocada mientras se reclamaba")
        self.habilitar(bloqueado)
        fallos = self.session.scalars(
            select(OperacionInfra).where(
                OperacionInfra.nodo_id == nodo.id,
                OperacionInfra.estado == "FALLO",
            )
        )
        if any(
            f.resultado
            and f.resultado.get("codigo_error")
            in {
                "LEASE_VENCIDA",
                "ESTADO_NODO_CAMBIO",
            }
            for f in fallos
        ):
            return None
        pendientes = list(
            self.session.scalars(
                select(OperacionInfra)
                .where(
                    OperacionInfra.nodo_id == nodo.id,
                    OperacionInfra.estado.in_(["PENDIENTE", "EJECUTANDO"]),
                )
                .order_by(OperacionInfra.created_at)
            )
        )
        for operacion in pendientes:
            if operacion.estado == "EJECUTANDO":
                if operacion.lease_hasta and en_utc(operacion.lease_hasta) < datetime.now(UTC):
                    operacion.estado = "FALLO"
                    operacion.resultado = {"codigo_error": "LEASE_VENCIDA"}
                    operacion.finalizada_at = datetime.now(UTC)
                    self.session.add(evento_operacion(operacion))
                    self.guardar()
                return None  # Nunca volver a ejecutar automáticamente un comando incierto.
        for operacion in pendientes:
            if operacion.grupo_id:
                anteriores = list(
                    self.session.scalars(
                        select(OperacionInfra).where(
                            OperacionInfra.grupo_id == operacion.grupo_id,
                            OperacionInfra.orden < operacion.orden,
                        )
                    )
                )
                if any(a.estado != "EXITO" for a in anteriores):
                    continue
            if operacion.tipo != "BACKUP" and (
                nodo.migracion_instalada != operacion.parametros.get("migracion_anterior")
                or nodo.version_instalada != operacion.parametros.get("version_anterior")
            ):
                operacion.estado = "FALLO"
                operacion.resultado = {"codigo_error": "ESTADO_NODO_CAMBIO"}
                operacion.finalizada_at = datetime.now(UTC)
                self.session.add(evento_operacion(operacion))
                self.guardar()
                return None
            lease = secrets.token_urlsafe(48)
            operacion.lease_hash = hashlib.sha256(lease.encode()).hexdigest()
            operacion.lease_hasta = datetime.now(UTC) + timedelta(
                seconds=self.settings.infra_lease_segundos
            )
            operacion.iniciada_at = datetime.now(UTC)
            operacion.estado = "EJECUTANDO"
            self.guardar()
            return {
                "id": str(operacion.id),
                "tipo": operacion.tipo,
                "parametros": operacion.parametros,
                "lease": lease,
                "lease_hasta": en_utc(operacion.lease_hasta).isoformat(),
            }
        return None

    def resultado(
        self,
        nodo: NodoInfraestructura,
        operacion_id: uuid.UUID,
        datos: ResultadoOperacionIn,
    ) -> OperacionInfra:
        operacion = self.session.scalar(
            select(OperacionInfra)
            .where(
                OperacionInfra.id == operacion_id,
                OperacionInfra.nodo_id == nodo.id,
            )
            .with_for_update()
        )
        if operacion is None:
            raise HTTPException(404, "Operación no encontrada para este nodo")
        if not operacion.lease_hash or not secrets.compare_digest(
            operacion.lease_hash,
            hashlib.sha256(datos.lease.encode()).hexdigest(),
        ):
            raise HTTPException(401, "Lease inválida")
        resultado = datos.model_dump(mode="json", exclude={"lease"})
        if operacion.estado in {"EXITO", "FALLO"}:
            if operacion.resultado != resultado:
                raise HTTPException(409, "La operación ya tiene otro resultado")
            return operacion
        if (
            operacion.estado != "EJECUTANDO"
            or not operacion.lease_hasta
            or (en_utc(operacion.lease_hasta) < datetime.now(UTC))
        ):
            raise HTTPException(409, "Lease vencida: revisar manualmente el estado del nodo")
        if datos.estado == "EXITO":
            if operacion.tipo == "BACKUP":
                if (
                    not datos.objeto
                    or not datos.sha256
                    or not datos.bytes
                    or not datos.dump_verificado
                ):
                    raise HTTPException(422, "Backup sin evidencia de integridad")
                self.session.add(
                    BackupInfra(
                        nodo_id=nodo.id,
                        operacion_id=operacion.id,
                        estado="VERIFICADO",
                        objeto=datos.objeto,
                        sha256=datos.sha256,
                        bytes=datos.bytes,
                        version=nodo.version_instalada,
                        migracion=nodo.migracion_instalada,
                        retencion_dias=int(str(operacion.parametros["retencion_dias"])),
                    )
                )
            elif not (
                datos.backend_ok
                and datos.base_datos_ok
                and datos.imagen_verificada
                and datos.migracion == operacion.parametros["migracion"]
            ):
                raise HTTPException(422, "Despliegue sin evidencia de imagen, salud y migración")
            else:
                nodo.version_instalada = str(operacion.parametros["version"])
                nodo.migracion_instalada = datos.migracion
                nodo.ultimo_despliegue = datetime.now(UTC)
        operacion.estado = datos.estado
        operacion.resultado = resultado
        operacion.finalizada_at = datetime.now(UTC)
        self.session.add(evento_operacion(operacion))
        self.guardar()
        return operacion


def evento_operacion(operacion: OperacionInfra) -> EventoInfraestructura:
    return EventoInfraestructura(
        actor_cuenta_id=operacion.actor_cuenta_id,
        correlacion_id=operacion.solicitud_id,
        accion="infra.operacion.resultado",
        recurso_id=operacion.id,
        resultado=operacion.estado,
        datos={"tipo": operacion.tipo, "nodo_id": str(operacion.nodo_id)},
    )
