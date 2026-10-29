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
    toneladas_declaradas: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=3
    )
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
    precio_acuerdo_embarcacion_confirmado: bool
    precio_acuerdo_aceptado: bool
    precio_ajuste_pendiente: bool
    precio_confirmado: Decimal | None
    precio_confirmado_por: str | None
    precio_confirmado_at: datetime | None
    modalidad_pago_cuadrilla: str | None
    monto_pago_cuadrilla: Decimal | None
    descarga_prevista: datetime | None
    llegada_planta_prevista: datetime | None
    jefe_bahia: str | None
    encargado_muelle: str | None
    apuntador: str | None
    responsable_pesaje_muelle: str | None
    responsable_pesaje_muelle_cuenta_id: uuid.UUID | None
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
    acepta_acuerdo: bool

    @model_validator(mode="after")
    def exigir_aceptacion(self) -> "ConfirmarPrecioIn":
        if not self.acepta_acuerdo:
            raise ValueError(
                "El Jefe de Bahía o Gerente debe aceptar el precio confirmado por la embarcación"
            )
        return self


class ConfirmarAcuerdoEmbarcacionIn(BaseModel):
    confirma_precio_acordado: bool

    @model_validator(mode="after")
    def exigir_confirmacion(self) -> "ConfirmarAcuerdoEmbarcacionIn":
        if not self.confirma_precio_acordado:
            raise ValueError(
                "Confirma que el precio ingresado corresponde al acuerdo con Jefe de "
                "Bahía o Gerente"
            )
        return self


class SolicitarAjustePrecioIn(BaseModel):
    precio_acordado: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    motivo: str = Field(min_length=5, max_length=1000)


class RegistrarFacturaIn(BaseModel):
    serie: str = Field(min_length=1, max_length=20)
    correlativo: str = Field(min_length=1, max_length=30)


RolPesca = Literal[
    "JEFE_BAHIA",
    "GERENTE",
    "ENCARGADO_MUELLE",
    "ARMADOR",
    "PATRON",
    "APUNTADOR_MUELLE",
    "APUNTADOR_PLANTA",
    "JEFE_CUADRILLA",
    "SECRETARIA",
    "TRAMITADORA",
    "TRANSPORTISTA",
]

ActividadCuadrilla = Literal["LAVADO", "CAJEO", "ESTIBA"]
EstadoActividadCuadrilla = Literal["EN_PROCESO", "COMPLETA", "INCIDENCIA"]


class AsignacionCuadrillaIn(BaseModel):
    nombre_integrante: str = Field(min_length=1, max_length=200)
    actividad: ActividadCuadrilla
    activa: bool = True
    monto_pago: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)


class AsignacionCuadrillaOut(Orm):
    id: uuid.UUID
    nombre_integrante: str
    actividad: ActividadCuadrilla
    activa: bool
    monto_pago: Decimal | None


class PagoCuadrillaIn(BaseModel):
    modalidad: Literal["UNICO", "DESGLOSE"]
    monto_unico: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)

    @model_validator(mode="after")
    def validar_monto_unico(self) -> "PagoCuadrillaIn":
        if self.modalidad == "UNICO" and self.monto_unico is None:
            raise ValueError("Indica el monto único que se entrega al Jefe de Cuadrilla")
        if self.modalidad == "DESGLOSE" and self.monto_unico is not None:
            raise ValueError("En modalidad por desglose, los montos se registran por integrante")
        return self


class ResponsablePesajeMuelleIn(BaseModel):
    rol: Literal["APUNTADOR_MUELLE", "ENCARGADO_MUELLE"]
    cuenta_id: uuid.UUID


class CuentaResponsablePesaje(BaseModel):
    cuenta_id: uuid.UUID
    rol: Literal["APUNTADOR_MUELLE", "ENCARGADO_MUELLE"]
    codigo: str
    nombre: str


class ActividadCuadrillaIn(BaseModel):
    actividad: Literal["LAVADO", "CAJEO", "ESTIBA"]
    estado: EstadoActividadCuadrilla
    cajas: int | None = Field(default=None, ge=0)
    hielo_kg: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=3)
    verificacion_visual: bool | None = None
    contaminacion_detectada: bool | None = None
    revision_final: bool | None = None
    observacion: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validar_datos_por_actividad(self) -> "ActividadCuadrillaIn":
        if self.estado == "INCIDENCIA" and not self.observacion:
            raise ValueError("Describe la incidencia para dejar constancia en la operación")
        if self.actividad == "LAVADO" and self.verificacion_visual is None:
            raise ValueError("El Lavador debe registrar la revisión visual")
        if (
            self.actividad == "LAVADO"
            and self.estado == "COMPLETA"
            and not self.verificacion_visual
        ):
            raise ValueError(
                "El lavado no puede marcarse completo si la revisión visual no fue satisfactoria"
            )
        if self.actividad == "CAJEO" and (
            self.cajas is None or self.contaminacion_detectada is None
        ):
            raise ValueError("El Cajeador debe registrar cajas y declarar si detectó contaminación")
        if self.actividad == "CAJEO" and self.contaminacion_detectada and not self.observacion:
            raise ValueError("Describe lo observado cuando se reporta contaminación")
        if self.actividad == "ESTIBA" and (
            self.cajas is None or self.hielo_kg is None or self.revision_final is None
        ):
            raise ValueError("El Estibador debe registrar cajas, hielo y revisión final")
        if self.actividad == "ESTIBA" and self.estado == "COMPLETA" and not self.revision_final:
            raise ValueError(
                "La tarea no puede marcarse completa sin una revisión final satisfactoria"
            )
        return self


class ActividadCuadrillaOut(Orm):
    id: uuid.UUID
    vehiculo_id: uuid.UUID
    actividad: str
    estado: str
    cajas: int | None
    hielo_kg: Decimal | None
    verificacion_visual: bool | None
    contaminacion_detectada: bool | None
    revision_final: bool | None
    observacion: str | None
    actor_cuenta_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class RolPescaAsignacionIn(BaseModel):
    cuenta_id: uuid.UUID
    rol: RolPesca
    activa: bool = True


class RolPescaAsignacionOut(Orm):
    id: uuid.UUID
    cuenta_id: uuid.UUID
    rol: RolPesca
    activa: bool
    codigo: str
    nombre: str


class CuentaPescaCandidata(BaseModel):
    cuenta_id: uuid.UUID
    codigo: str
    nombre: str


class RolesPescaActuales(BaseModel):
    cuenta_id: uuid.UUID
    roles: list[RolPesca]


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
    tipo_gasto: Literal["MUELLE", "HIELO", "FLETE", "CUADRILLA", "APUNTADOR", "OTRO"] | None = None
    tipo_comprobante: Literal["factura", "boleta", "recibo_honorarios"] | None = None
    motivo_boleta_muelle: str | None = Field(default=None, max_length=500)
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
        es_gasto = self.clase in {"gasto_empresa", "gasto_bahia_reembolsable"}
        if es_gasto and (self.tipo_gasto is None or self.tipo_comprobante is None):
            raise ValueError("Todo gasto operativo debe clasificarse y tener un CPE definido")
        comprobante_por_gasto = {
            "MUELLE": "factura",
            "HIELO": "factura",
            "FLETE": "factura",
            "CUADRILLA": "recibo_honorarios",
            "APUNTADOR": "recibo_honorarios",
        }
        if es_gasto and self.tipo_gasto in comprobante_por_gasto:
            esperado = comprobante_por_gasto[self.tipo_gasto]
            boleta_excepcional = (
                self.tipo_gasto == "MUELLE"
                and self.tipo_comprobante == "boleta"
                and bool(self.motivo_boleta_muelle and self.motivo_boleta_muelle.strip())
            )
            if self.tipo_comprobante != esperado and not boleta_excepcional:
                raise ValueError(
                    f"{self.tipo_gasto}: el comprobante requerido es {esperado}; solo admite "
                    "boleta para muelle si no puede emitir factura y se explica el motivo"
                )
        if self.tipo_comprobante == "boleta" and (
            self.tipo_gasto != "MUELLE"
            or not self.motivo_boleta_muelle
            or not self.motivo_boleta_muelle.strip()
        ):
            raise ValueError(
                "La boleta solo se admite para el muelle cuando no puede emitir factura; "
                "explica la excepción"
            )
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
    tipo_gasto: str | None
    tipo_comprobante: str | None
    motivo_boleta_muelle: str | None
    importe: Decimal
    moneda: str
    cantidad: Decimal | None
    tarifa_unitaria: Decimal | None
    comprobante_documento_id: uuid.UUID | None
    voucher_documento_id: uuid.UUID | None
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
    voucher_documento_id: uuid.UUID | None
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
        if not {
            "fecha_reporte_planta",
            "llegada_planta",
            "inicio_planta",
            "fin_planta",
        }.intersection(self.model_fields_set):
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
            raise ValueError(
                "El peso aceptado debe ser mayor que cero para un resultado completo o parcial"
            )
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
    etapa: str
    nombre: str
    mime_type: str
    sha256: str
    subido_por: str
    estado_revision: Literal["PENDIENTE", "VERIFICADO", "OBSERVADO"]
    observacion_revision: str | None
    revisado_por: str | None
    revisado_at: datetime | None
    version: int
    vigente: bool
    documento_anterior_id: uuid.UUID | None
    created_at: datetime


class RevisionDocumentoIn(BaseModel):
    estado: Literal["VERIFICADO", "OBSERVADO"]
    observacion: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validar_observacion(self) -> "RevisionDocumentoIn":
        if self.estado == "OBSERVADO" and not (self.observacion or "").strip():
            raise ValueError("Indica el motivo de la observación")
        return self


class CierreOut(BaseModel):
    estado: str
    mensaje: str


class DiferenciaPlantaOut(BaseModel):
    vehiculo_id: uuid.UUID
    estado: Literal["verde", "naranja", "rojo", "sin_comparacion"]
    peso_aceptado_kg: Decimal
    peso_muelle_kg: Decimal | None
    diferencia_kg: Decimal | None
