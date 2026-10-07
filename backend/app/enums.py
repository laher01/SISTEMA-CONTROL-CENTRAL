from enum import StrEnum


class TipoDocumento(StrEnum):
    FACT = "FACT"
    RHE = "RHE"
    GRR = "GRR"
    GRT = "GRT"
    VCHR = "VCHR"
    RET = "RET"
    EMAIL = "EMAIL"
    WSP = "WSP"
    COT = "COT"
    OC = "OC"
    REQ = "REQ"
    FOTO = "FOTO"
    OTRO = "OTRO"


class TipoComprobante(StrEnum):
    FACT = "FACT"
    RHE = "RHE"


class Moneda(StrEnum):
    PEN = "PEN"
    USD = "USD"


class EstadoExpediente(StrEnum):
    VERDE = "VERDE"
    AMARILLO = "AMARILLO"
    NARANJA = "NARANJA"
    ROJO = "ROJO"


class EstadoDocumento(StrEnum):
    PENDIENTE_CLASIFICACION = "PENDIENTE_CLASIFICACION"
    PENDIENTE_RELACION = "PENDIENTE_RELACION"
    RELACIONADO = "RELACIONADO"


class TipoAlerta(StrEnum):
    BANCARIZACION_SIN_VOUCHER = "BANCARIZACION_SIN_VOUCHER"
    RETENCION_PENDIENTE = "RETENCION_PENDIENTE"
    RECEPTOR_NO_AUTORIZADO = "RECEPTOR_NO_AUTORIZADO"
    EXPEDIENTE_VENCIDO = "EXPEDIENTE_VENCIDO"


class RolMiembro(StrEnum):
    ADMINISTRADOR = "ADMINISTRADOR"
    GERENTE = "GERENTE"
    SECRETARIA = "SECRETARIA"
    USUARIO = "USUARIO"
