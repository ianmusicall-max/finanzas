import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lector import NoEntendi, _numero, interpretar  # noqa: E402

HOY = date(2026, 9, 30)


def leer(t, tipo=None):
    return interpretar(t, tipo, base=HOY)


class Montos(unittest.TestCase):
    def test_formatos(self):
        for texto, n in [("45", 45), ("12.50", 12.5), ("12,50", 12.5), ("1,500", 1500), ("1.500", 1500),
                         ("1,234.56", 1234.56), ("1.234,56", 1234.56), ("2500", 2500)]:
            self.assertEqual(_numero(texto), n, texto)

    def test_k_multiplica(self):
        self.assertEqual(leer("2k laptop").monto, 2000)


class Gastos(unittest.TestCase):
    def test_simple(self):
        m = leer("45 almuerzo")
        self.assertEqual((m.tipo, m.monto, m.moneda, m.categoria, m.descripcion, m.fecha),
                         ("Gasto", 45, "PEN", "Comida y restaurantes", "Almuerzo", HOY))
        self.assertTrue(m.adivinada)

    def test_medio_y_ayer(self):
        m = leer("12.50 taxi yape ayer")
        self.assertEqual((m.monto, m.categoria, m.medio, m.fecha, m.descripcion),
                         (12.5, "Movilidad", "Yape", date(2026, 9, 29), "Taxi"))

    def test_monto_al_final(self):
        m = leer("netflix 44.90")
        self.assertEqual((m.monto, m.categoria), (44.9, "Suscripciones"))

    def test_dolares(self):
        for t in ("20 usd netflix", "$20 netflix", "20$ netflix", "20 dolares netflix"):
            m = leer(t)
            self.assertEqual((m.monto, m.moneda, m.descripcion), (20, "USD", "Netflix"), t)

    def test_soles_explicito(self):
        m = leer("s/ 35 menu")
        self.assertEqual((m.monto, m.moneda), (35, "PEN"))

    def test_fecha_dd_mm(self):
        self.assertEqual(leer("30 cine 15/09").fecha, date(2026, 9, 15))
        self.assertEqual(leer("30 cine 28/12").fecha, date(2025, 12, 28))   # diciembre que viene: es el pasado

    def test_sin_categoria_cae_en_otros(self):
        m = leer("80 cosas raras")
        self.assertEqual(m.categoria, "Otros")
        self.assertFalse(m.adivinada)

    def test_la_palabra_mas_larga_gana(self):
        self.assertEqual(leer("15 pasaje metropolitano").categoria, "Movilidad")
        self.assertEqual(leer("300 supermercado").categoria, "Supermercado")

    def test_rublos_y_tinkoff(self):
        for t in ("1200 rub pyaterochka tinkoff", "1200₽ pyaterochka tinkoff", "1200 rublos pyaterochka tinkoft"):
            m = leer(t)
            self.assertEqual((m.monto, m.moneda, m.categoria, m.medio), (1200, "RUB", "Supermercado", "T-Bank"), t)

    def test_sin_monto(self):
        with self.assertRaises(NoEntendi):
            leer("almuerzo")

    def test_fecha_imposible(self):
        with self.assertRaises(NoEntendi):
            leer("20 taxi 31/02")


class OtrosTipos(unittest.TestCase):
    def test_ingreso_con_mas(self):
        m = leer("+1943 usd facebook")
        self.assertEqual((m.tipo, m.monto, m.moneda, m.categoria), ("Ingreso", 1943, "USD", "Facebook"))

    def test_sueldo_sin_mas(self):
        m = leer("3500 sueldo")
        self.assertEqual((m.tipo, m.categoria), ("Ingreso", "Sueldo"))

    def test_facebook_sin_mas_es_gasto(self):
        # sin '+' "facebook ads" es publicidad pagada, no un cobro
        m = leer("150 facebook ads")
        self.assertEqual(m.tipo, "Gasto")

    def test_ahorro(self):
        m = leer("ahorro 500 emergencia")
        self.assertEqual((m.tipo, m.monto, m.categoria, m.descripcion), ("Ahorro", 500, "Fondo de emergencia", "Emergencia"))

    def test_inversion(self):
        m = leer("inversion 1000 fondo mutuo")
        self.assertEqual((m.tipo, m.categoria), ("Inversión", "Fondos y acciones"))

    def test_tipo_forzado(self):
        self.assertEqual(leer("100 regalo de mama", "Ingreso").tipo, "Ingreso")


if __name__ == "__main__":
    unittest.main()


class MediosNuevos(unittest.TestCase):
    def test_alias(self):
        for texto, medio in (("50 taxi cmr", "Falabella"), ("50 taxi falabella", "Falabella"),
                             ("50 taxi t bank", "T-Bank"), ("50 taxi tbank", "T-Bank"), ("50 taxi tinkoff", "T-Bank"),
                             ("50 comision kucoin", "KuCoin"), ("50 cuota sip", "SIP")):
            self.assertEqual(interpretar(texto).medio, medio, texto)
