"""Pruebas unitarias para el núcleo lógico, independientes de la base de datos."""

import unittest
from decimal import Decimal

from app.services.contabilidad_items_rules import (
    Accion,
    DecisionAuditoria,
    EstadoAuditoria,
    LineaFactura,
    acumulados_validos,
    sugerir_categoria,
    validar_decision,
)


class ContabilidadItemsTests(unittest.TestCase):
    def test_categorias_sugeridas_no_invalidan(self):
        self.assertEqual(sugerir_categoria("5 paquetes de agua San Carlos"), "BEBIDAS")
        self.assertEqual(sugerir_categoria("Leche Gloria evaporada 400g"), "LACTEOS")
        self.assertEqual(sugerir_categoria("Cadena para perro"), "POR_CATEGORIZAR")

    def test_suma_y_reprocesamiento(self):
        a = LineaFactura("fact-1", "line-1", "tenant-1", "agua", Decimal("5"), "PAQUETE")
        b = LineaFactura("fact-2", "line-1", "tenant-1", "agua", Decimal("7"), "PAQUETE")
        otro = LineaFactura("fact-3", "line-1", "tenant-2", "agua", Decimal("90"), "PAQUETE")
        estados = {
            "fact-1": EstadoAuditoria.VIGENTE,
            "fact-2": EstadoAuditoria.VIGENTE,
            "fact-3": EstadoAuditoria.VIGENTE,
        }
        resultado = acumulados_validos([a, a, b, otro], estados, "tenant-1")
        self.assertEqual(resultado, {("agua", "PAQUETE"): Decimal("12")})

    def test_invalidacion_excluye_factura_completa(self):
        items = [
            LineaFactura("f", "1", "t", "leche", Decimal("10"), "CAJA"),
            LineaFactura("f", "2", "t", "juguetes", Decimal("1"), "UNIDAD"),
        ]
        pendiente = {"f": EstadoAuditoria.INVALIDADA_PENDIENTE}
        confirmada = {"f": EstadoAuditoria.INVALIDADA_CONFIRMADA}
        vigente = {"f": EstadoAuditoria.VIGENTE}
        self.assertEqual(acumulados_validos(items, pendiente, "t"), {})
        self.assertEqual(acumulados_validos(items, confirmada, "t"), {})
        self.assertEqual(len(acumulados_validos(items, vigente, "t")), 2)

    def test_secretaria_no_concilia(self):
        decision = DecisionAuditoria(
            Accion.APROBAR, "secretaria-1", "SECRETARIA", "secretaria-2", "SECRETARIA"
        )
        with self.assertRaises(PermissionError):
            validar_decision(decision)

    def test_gerencia_no_autoaprueba(self):
        decision = DecisionAuditoria(Accion.APROBAR, "actor-1", "GERENCIA", "actor-1", "SECRETARIA")
        with self.assertRaises(PermissionError):
            validar_decision(decision)

    def test_gerencia_aprueba_accion_secretaria(self):
        decision = DecisionAuditoria(
            Accion.APROBAR, "gerente", "GERENCIA", "secretaria", "SECRETARIA"
        )
        validar_decision(decision)


if __name__ == "__main__":
    unittest.main()
