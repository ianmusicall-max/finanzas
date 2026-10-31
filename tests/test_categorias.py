"""Categorias y medios de pago."""

import sys
import os
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import categorias as C  # noqa: E402


@unittest.skipIf(os.environ.get("PERFIL", "jose") != "jose",
                 "la tarjeta Sip es del perfil de José")
class TarjetaOhEsSip(unittest.TestCase):
    """El banco renombró la Tarjeta OH a Sip (21/10/2026). Era un solo producto, no dos.

    Antes el medio "Tarjeta OH" mandaba lo comprado a crédito a una deuda "Tarjeta OH" y el medio
    "SIP" a una "Tarjeta SIP"; ninguna de las dos existía, así que las compras no llegaban nunca a
    "Banco SIP", que es la fila que tiene la deuda de verdad.
    """

    def test_las_dos_formas_caen_en_banco_sip(self):
        self.assertEqual(C.deuda_de_tarjeta("SIP"), "Banco SIP")
        self.assertEqual(C.deuda_de_tarjeta("Tarjeta OH"), "Banco SIP")   # movimientos viejos

    def test_el_acreedor_tambien(self):
        for medio in ("SIP", "Tarjeta OH"):
            self.assertEqual(C.BANCO_TARJETA[medio], "Banco SIP")

    def test_escribir_oh_sigue_sirviendo(self):
        for texto in ("45 almuerzo oh credito", "30 cafe tarjeta oh", "200 zapatos sip"):
            self.assertEqual(C.buscar_medio(texto), "SIP", texto)

    def test_ya_no_se_puede_elegir_la_tarjeta_vieja(self):
        self.assertNotIn("Tarjeta OH", C.MEDIOS)
        self.assertNotIn("Tarjeta OH", C.TARJETAS)
        self.assertIn("SIP", C.TARJETAS)
