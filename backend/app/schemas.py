import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.enums import (
    EstadoDocumento,
    EstadoExpediente,
    Moneda,
    RolMiembro,
    TipoAlerta,
    TipoComprobante,
    TipoDocumento,
)

Ruc = Annotated[str, Field(pattern=r"^\d{11}$")]


class Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EmpresaIn(BaseModel):
    ruc: Ruc
    razon_social: str = Field(min_length=1, max_length=300)


class EmpresaOut(Orm):
    id: uuid.UUID
    ruc: str
    razon_social: str
    autorizada: bool
    agente_retencion: bool


class EmpresaActualizar(BaseModel):
    razon_social: str | None = Field(default=None, min_length=1, max_length=300)
    autorizada: bool | None = None
    agente_retencion: bool | None = None


class MiembroIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=200)
    rol: RolMiembro


class MiembroOut(Orm):
    id: uuid.UUID
    codigo: str
    nombre: str
    rol: RolMiembro
    activo: bool


class GestorIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=200)
    usuario_id: uuid.UUID


class GestorOut(Orm):
    id: uuid.UUID
    codigo: str
    nombre: str
    usuario_id: uuid.UUID | None


class DocumentoOut(Orm):
    id: uuid.UUID
    expediente_id: uuid.UUID | None
    tipo_documento: TipoDocumento | None
    estado: EstadoDocumento
    sha256: str
    nombre_original: str
    mime_type: str
    tamano_bytes: int
    datos_extraidos: dict[str, object] | None
    gestor_id: uuid.UUID | None
    usuario_id: uuid.UUID | None
    created_at: datetime


class DocumentoVincular(BaseModel):
    expediente_id: uuid.UUID
    tipo_documento: TipoDocumento


class ProcesamientoLoteOut(BaseModel):
    considerados: int
    relacionados: int
    revision_requerida: int
    fallidos: int


class ExtraccionConfirmar(BaseModel):
    serie: str | None = Field(default=None, pattern=r"^[A-Z0-9]{4}$")
    correlativo: str | None = Field(default=None, pattern=r"^\d{1,8}$")
    ruc_emisor: Ruc | None = None
    ruc_receptor: Ruc | None = None
    fecha_emision: date | None = None
    moneda: Moneda | None = None
    importe_total: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    numero_operacion: str | None = Field(default=None, min_length=4, max_length=30)

    @model_validator(mode="after")
    def contiene_algun_campo(self) -> "ExtraccionConfirmar":
        if not self.model_fields_set:
            raise ValueError("Debe confirmar al menos un campo")
        return self


class ExpedienteAsistidoIn(BaseModel):
    tipo_comprobante: TipoComprobante
    razon_social_emisor: str | None = Field(default=None, min_length=1, max_length=300)
    razon_social_receptor: str | None = Field(default=None, min_length=1, max_length=300)
    requiere_guia: bool = True
    gestor_id: uuid.UUID | None = None


class AlertaOut(Orm):
    id: uuid.UUID
    expediente_id: uuid.UUID
    tipo: TipoAlerta
    mensaje: str
    resuelta: bool
    created_at: datetime
    resuelta_at: datetime | None


class ExpedienteIn(BaseModel):
    receptor: EmpresaIn
    emisor: EmpresaIn
    tipo_comprobante: TipoComprobante
    serie: str = Field(pattern=r"^[A-Z0-9]{4}$")
    correlativo: str = Field(pattern=r"^\d{1,8}$")
    fecha_emision: date
    moneda: Moneda = Moneda.PEN
    importe_total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    requiere_guia: bool = True
    gestor_id: uuid.UUID | None = None


class ExpedienteOut(Orm):
    id: uuid.UUID
    receptor: EmpresaOut
    emisor: EmpresaOut
    tipo_comprobante: TipoComprobante
    serie: str
    correlativo: str
    fecha_emision: date
    moneda: Moneda
    importe_total: Decimal
    requiere_guia: bool
    gestor_id: uuid.UUID | None
    usuario_id: uuid.UUID | None
    estado: EstadoExpediente
    pendiente_aprobacion: bool
    created_at: datetime


class ExpedienteAsistidoOut(BaseModel):
    expediente: ExpedienteOut
    documento: DocumentoOut
    creado: bool


class ExpedienteDetalle(ExpedienteOut):
    documentos: list[DocumentoOut]
    alertas: list[AlertaOut]
    faltantes: list[TipoDocumento]
    fecha_limite: date


class RelacionSugeridaOut(BaseModel):
    expediente: ExpedienteOut
    puntaje: float = Field(ge=0, le=1)
    evidencias: list[str]


class Recalculo(BaseModel):
    actualizados: int


class MontosMoneda(BaseModel):
    moneda: Moneda
    bancarizable: Decimal
    no_bancarizable: Decimal


class DashboardResumen(BaseModel):
    expedientes_total: int
    por_estado: dict[EstadoExpediente, int]
    pendientes_aprobacion: int
    montos: list[MontosMoneda]
    alertas_abiertas: dict[TipoAlerta, int]
    documentos_pendientes: dict[EstadoDocumento, int]


class ProduccionFila(BaseModel):
    usuario_id: uuid.UUID | None
    usuario_codigo: str
    usuario_nombre: str
    gestor_id: uuid.UUID | None
    gestor_codigo: str
    gestor_nombre: str
    moneda: Moneda
    expedientes: int
    importe_total: Decimal


class ProduccionResumen(BaseModel):
    filas: list[ProduccionFila]


class ComprasProveedorFila(BaseModel):
    usuario_codigo: str
    gestor_codigo: str
    emisor_ruc: str
    emisor_razon_social: str
    receptor_ruc: str
    receptor_razon_social: str
    moneda: Moneda
    expedientes: int
    importe_total: Decimal
