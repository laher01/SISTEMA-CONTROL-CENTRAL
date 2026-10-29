import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OperacionIn(BaseModel):
    fecha_reporte: date | None = None
    puerto: str = Field(min_length=1, max_length=100)
    muelle: str = Field(min_length=1, max_length=200)
    planta: str = Field(min_length=1, max_length=200)
    armador_reportante: str | None = Field(default=None, max_length=200)
    comprador: str | None = Field(default=None, max_length=200)
    remitente: str | None = Field(default=None, max_length=200)
    destinatario: str | None = Field(default=None, max_length=200)
    facturador: str | None = Field(default=None, max_length=200)
    toneladas_declaradas: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=3)
    precio_propuesto: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    descarga_prevista: datetime | None = None
    llegada_planta_prevista: datetime | None = None
    jefe_bahia: str | None = Field(default=None, max_length=200)
    encargado_muelle: str | None = Field(default=None, max_length=200)
    apuntador: str | None = Field(default=None, max_length=200)
    observacion: str | None = None


class OperacionOut(Orm):
    id: uuid.UUID
    fecha_reporte: date
    puerto: str
    muelle: str
    planta: str
    armador_reportante: str | None
    comprador: str | None
    remitente: str | None
    destinatario: str | None
    facturador: str | None
    toneladas_declaradas: Decimal | None
    precio_propuesto: Decimal | None
    precio_confirmado: Decimal | None
    precio_confirmado_por: str | None
    precio_confirmado_at: datetime | None
    descarga_prevista: datetime | None
    llegada_planta_prevista: datetime | None
    jefe_bahia: str | None
    encargado_muelle: str | None
    apuntador: str | None
    factura_serie: str | None
    factura_correlativo: str | None
    factura_emitida_at: datetime | None
    factura_emitida_por: str | None
    estado_facturacion: str
    responsable_id: str
    estado: str
    observacion: str | None
    created_at: datetime


class EmbarcacionIn(BaseModel):
    matricula: str = Field(min_length=1, max_length=40)
    nombre: str = Field(min_length=1, max_length=200)
    armador: str = Field(min_length=1, max_length=200)
    patron: str = Field(min_length=1, max_length=200)
    intermediario: str | None = Field(default=None, max_length=200)
    inicio_descarga: datetime | None = None
    fin_descarga: datetime | None = None
    peso_declarado_kg: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=3)


class TiemposDescargaIn(BaseModel):
    inicio_descarga: datetime | None = None
    fin_descarga: datetime | None = None
    observacion: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def requiere_fecha(self) -> "TiemposDescargaIn":
        if not {"inicio_descarga", "fin_descarga"}.intersection(self.model_fields_set):
            raise ValueError("Indique al menos una fecha u hora de descarga")
        return self


class ConfirmarPrecioIn(BaseModel):
    precio_confirmado: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    comprador: str = Field(min_length=1, max_length=200)


class RegistrarFacturaIn(BaseModel):
    serie: str = Field(min_length=1, max_length=20)
    correlativo: str = Field(min_length=1, max_length=30)


class MovimientoIn(BaseModel):
    operacion_id: uuid.UUID | None = None
    clase: Literal[
        "gasto_empresa",
        "gasto_bahia_reembolsable",
        "adelanto_armador_empresa",
        "prestamo_personal_bahia",
    ]
    pagador: str = Field(min_length=1, max_length=200)
    beneficiario: str = Field(min_length=1, max_length=200)
    concepto: str = Field(min_length=1, max_length=300)
    importe: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    moneda: Literal["PEN", "USD"] = "PEN"
    cantidad: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3)
    tarifa_unitaria: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)

    @model_validator(mode="after")
    def separar_prestamo_personal(self) -> "MovimientoIn":
        es_prestamo = self.clase == "prestamo_personal_bahia"
        if es_prestamo and self.operacion_id is not None:
            raise ValueError("El préstamo personal no puede vincularse a una operación de pesca")
        if not es_prestamo and self.operacion_id is None:
            raise ValueError("Este movimiento debe pertenecer a una operación")
        return self


class AbonoMovimientoIn(BaseModel):
    importe: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    observacion: str | None = Field(default=None, max_length=1000)


class MovimientoOut(Orm):
    id: uuid.UUID
    operacion_id: uuid.UUID | None
    clase: str
    pagador: str
    beneficiario: str
    concepto: str
    importe: Decimal
    moneda: str
    cantidad: Decimal | None
    tarifa_unitaria: Decimal | None
    comprobante_documento_id: uuid.UUID | None
    registrado_por: str
    created_at: datetime
    abonado: Decimal = Decimal("0")
    saldo: Decimal = Decimal("0")
    estado: str = "pendiente"


class AbonoMovimientoOut(Orm):
    id: uuid.UUID
    movimiento_id: uuid.UUID
    importe: Decimal
    tipo: str
    registrado_por: str
    observacion: str | None
    created_at: datetime


class DescargaOut(BaseModel):
    descarga_id: uuid.UUID
    embarcacion_id: uuid.UUID
    matricula: str
    nombre: str
    armador: str
    patron: str
    peso_declarado_kg: Decimal | None = None
    inicio_descarga: datetime | None = None
    fin_descarga: datetime | None = None


class VehiculoIn(BaseModel):
    placa: str = Field(min_length=1, max_length=20)
    tipo: str = Field(min_length=1, max_length=60)
    chofer: str = Field(min_length=1, max_length=200)
    turno: str | None = Field(default=None, max_length=80)


class TiemposPlantaIn(BaseModel):
    fecha_reporte_planta: date | None = None
    llegada_planta: datetime | None = None
    inicio_planta: datetime | None = None
    fin_planta: datetime | None = None
    observacion: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def campo_a_actualizar(self) -> "TiemposPlantaIn":
        if not {"fecha_reporte_planta", "llegada_planta", "inicio_planta", "fin_planta"}.intersection(self.model_fields_set):
            raise ValueError("Indique al menos una fecha u hora para actualizar")
        return self


class CargaIn(BaseModel):
    descarga_id: uuid.UUID
    peso_muelle_kg: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=3)
    cajas: int | None = Field(default=None, ge=0)
    observacion: str | None = None

    @model_validator(mode="after")
    def carga_con_un_dato(self) -> "CargaIn":
        if self.peso_muelle_kg is None and self.cajas is None:
            raise ValueError("Registre el peso de muelle o la cantidad de cajas")
        return self


class RegistroPlantaIn(BaseModel):
    resultado: Literal["completo", "parcial", "rechazado"]
    peso_aceptado: Decimal = Field(ge=0, max_digits=14, decimal_places=3)
    unidad: Literal["kg", "ton", "lb", "oz"] = "ton"
    cajas_rechazadas: int = Field(default=0, ge=0)
    motivo_rechazo: str | None = Field(default=None, max_length=200)
    fecha_finalizacion: datetime | None = None
    no_registrar_fecha_finalizacion: bool = False
    observacion: str | None = None

    @model_validator(mode="after")
    def validar_resultado(self) -> "RegistroPlantaIn":
        if self.resultado in {"completo", "parcial"} and self.peso_aceptado <= 0:
            raise ValueError("El peso aceptado debe ser mayor que cero para un resultado completo o parcial")
        if self.resultado == "rechazado" and not self.motivo_rechazo:
            raise ValueError("Indique el motivo del rechazo")
        if self.resultado == "completo" and self.cajas_rechazadas:
            raise ValueError("Un registro completo no puede tener cajas rechazadas")
        if self.no_registrar_fecha_finalizacion and self.fecha_finalizacion is not None:
            raise ValueError("Elija una fecha final o marque que no se registrará")
        return self


class RegistroPlantaOut(Orm):
    id: uuid.UUID
    vehiculo_id: uuid.UUID
    resultado: str
    peso_aceptado: Decimal
    unidad: str
    cajas_rechazadas: int
    motivo_rechazo: str | None
    fecha_finalizacion: datetime | None
    observacion: str | None
    created_at: datetime
    updated_at: datetime


class VehiculoOut(Orm):
    id: uuid.UUID
    operacion_id: uuid.UUID
    placa: str
    tipo: str
    chofer: str
    estado: str
    salida_muelle: datetime | None
    llegada_planta: datetime | None
    fecha_reporte_planta: date | None
    inicio_planta: datetime | None
    fin_planta: datetime | None
    turno: str | None


class DocumentoOut(Orm):
    id: uuid.UUID
    operacion_id: uuid.UUID | None
    vehiculo_id: uuid.UUID | None
    tipo: str
    nombre: str
    mime_type: str
    sha256: str
    subido_por: str
    created_at: datetime


class CierreOut(BaseModel):
    estado: str
    mensaje: str


class DiferenciaPlantaOut(BaseModel):
    vehiculo_id: uuid.UUID
    estado: Literal["verde", "naranja", "rojo", "sin_comparacion"]
    peso_aceptado_kg: Decimal
    peso_muelle_kg: Decimal | None
    diferencia_kg: Decimal | None
