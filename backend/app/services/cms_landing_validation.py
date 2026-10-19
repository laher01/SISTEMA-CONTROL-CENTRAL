"""Validación estricta de contenido comercial antes de persistir borradores."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def texto_seguro(valor: str) -> str:
    limpio = valor.strip()
    if not limpio or any(caracter in "<>" or (ord(caracter) < 32 and caracter not in "\t\n\r") for caracter in limpio):
        raise ValueError("Texto vacío, HTML o caracteres de control no permitidos")
    return limpio


class BeneficioCms(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    titulo: str = Field(min_length=1, max_length=140)
    descripcion: str = Field(min_length=1, max_length=450)

    @field_validator("titulo", "descripcion")
    @classmethod
    def validar_texto(cls, valor: str) -> str:
        return texto_seguro(valor)


class ContenidoCms(BaseModel):
    model_config = ConfigDict(extra="forbid")
    marca: str = Field(min_length=1, max_length=70)
    etiqueta: str = Field(min_length=1, max_length=120)
    titulo: str = Field(min_length=1, max_length=180)
    descripcion: str = Field(min_length=1, max_length=700)
    beneficiosTitulo: str = Field(min_length=1, max_length=180)
    beneficios: list[BeneficioCms] = Field(min_length=1, max_length=8)
    planesTitulo: str = Field(min_length=1, max_length=160)
    planesDescripcion: str = Field(min_length=1, max_length=700)
    registroTitulo: str = Field(min_length=1, max_length=160)
    registroDescripcion: str = Field(min_length=1, max_length=700)

    @field_validator(
        "marca", "etiqueta", "titulo", "descripcion", "beneficiosTitulo",
        "planesTitulo", "planesDescripcion", "registroTitulo", "registroDescripcion"
    )
    @classmethod
    def validar_texto(cls, valor: str) -> str:
        return texto_seguro(valor)

    @model_validator(mode="after")
    def validar_ids_unicos(self) -> "ContenidoCms":
        ids = [beneficio.id for beneficio in self.beneficios]
        if len(ids) != len(set(ids)):
            raise ValueError("Identificadores de beneficios repetidos")
        return self
