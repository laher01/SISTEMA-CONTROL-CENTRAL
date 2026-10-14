"""Pruebas unitarias para el núcleo lógico, independientes de la base de datos."""
import unittest
from decimal import Decimal
from app.services.contabilidad_items_rules import (
    Accion, DecisionAuditoria, EstadoAuditoria, LineaFactura,
    acumulados_validos, sugerir_categoria, validar_decision,
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
        estados = {"fact-1": EstadoAuditoria.VIGENTE, "fact-2": EstadoAuditoria.VIGENTE, "fact-3": EstadoAuditoria.VIGENTE}
        self.assertEqual(acumulados_validos([a, a, b, otro], estados, "tenant-1"), {("agua", "PAQUETE"): Decimal("12")})

    def test_invalidacion_excluye_factura_completa(self):
        items = [
            LineaFactura("f", "1", "t", "leche", Decimal("10"), "CAJA"),
            LineaFactura("f", "2", "t", "juguetes", Decimal("1"), "UNIDAD"),
        ]
        self.assertEqual(acumulados_validos(items, {"f": EstadoAuditoria.INVALIDADA_PENDIENTE}, "t"), {})
        self.assertEqual(acumulados_validos(items, {"f": EstadoAuditoria.INVALIDADA_CONFIRMADA}, "t"), {})
        self.assertEqual(len(acumulados_validos(items, {"f": EstadoAuditoria.VIGENTE}, "t")), 2)

    def test_secretaria_no_concilia(self):
        with self.assertRaises(PermissionError):
            validar_decision(DecisionAuditoria(Accion.APROBAR, "secretaria-1", "SECRETARIA", "secretaria-2", "SECRETARIA"))

    def test_gerencia_no_autoaprueba(self):
        with self.assertRaises(PermissionError):
            validar_decision(DecisionAuditoria(Accion.APROBAR, "actor-1", "GERENCIA", "actor-1", "SECRETARIA"))

    def test_gerencia_aprueba_accion_secretaria(self):
        validar_decision(DecisionAuditoria(Accion.APROBAR, "gerente", "GERENCIA", "secretaria", "SECRETARIA"))


if __name__ == "__main__":
    unittest.main()
