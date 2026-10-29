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
    observacion: str | None = None


class OperacionOut(Orm):
    id: uuid.UUID
    fecha_reporte: date
    puerto: str
    muelle: str
    planta: str
    responsable_id: str
    estado: str
    observacion: str | None
    created_at: datetime


class EmbarcacionIn(BaseModel):
    matricula: str = Field(min_length=1, max_length=40)
    nombre: str = Field(min_length=1, max_length=200)
    patron_armador: str = Field(min_length=1, max_length=200)
    intermediario: str | None = Field(default=None, max_length=200)
    inicio_descarga: datetime | None = None
    fin_descarga: datetime | None = None


class DescargaOut(BaseModel):
    descarga_id: uuid.UUID
    embarcacion_id: uuid.UUID
    matricula: str
    nombre: str


class VehiculoIn(BaseModel):
    placa: str = Field(min_length=1, max_length=20)
    tipo: str = Field(min_length=1, max_length=60)
    chofer: str = Field(min_length=1, max_length=200)
    fecha_reporte_planta: date | None = None
    inicio_planta: datetime | None = None
    turno: str | None = Field(default=None, max_length=80)


class TiemposPlantaIn(BaseModel):
    fecha_reporte_planta: date | None = None
    inicio_planta: datetime | None = None
    fin_planta: datetime | None = None
    observacion: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def campo_a_actualizar(self) -> "TiemposPlantaIn":
        if not {"fecha_reporte_planta", "inicio_planta", "fin_planta"}.intersection(self.model_fields_set):
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
    fecha_reporte_planta: date | None
    inicio_planta: datetime | None
    fin_planta: datetime | None
    turno: str | None


class DocumentoOut(Orm):
    id: uuid.UUID
    operacion_id: uuid.UUID
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
