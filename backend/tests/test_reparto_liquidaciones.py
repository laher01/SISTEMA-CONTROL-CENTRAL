import pytest

from app.services.reparto_liquidaciones import calcular_partidas


def test_reparto_multiples_beneficiarios_y_bases_independientes():
    r = calcular_partidas(
        [
            {"tipo": "GESTOR", "beneficiario": "Gestor A", "base": "60000", "porcentaje": "2.3750"},
            {"tipo": "GESTOR", "beneficiario": "Gestor B", "base": "40000", "porcentaje": "1.2500"},
            {
                "tipo": "EXTERNO",
                "beneficiario": "Servicio tercero",
                "base": "1000.00",
                "porcentaje": "5.00",
            },
        ]
    )
    assert r["total"] == "1975.00"
    assert [x["importe"] for x in r["partidas"]] == ["1425.00", "500.00", "50.00"]


@pytest.mark.parametrize(
    "base,tasa",
    [
        ("-1", "3"),
        ("1", "-3"),
        ("2", "100.01"),
        ("NaN", "1"),
        ("Infinity", "1"),
        ("1", "NaN"),
    ],
)
def test_rechaza_montos_invalidos(base, tasa):
    with pytest.raises(ValueError):
        calcular_partidas(
            [{"tipo": "GESTOR", "beneficiario": "A", "base": base, "porcentaje": tasa}]
        )


def test_sin_beneficiarios_rechazado():
    with pytest.raises(ValueError):
        calcular_partidas([])
