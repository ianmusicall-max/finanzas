import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import finanzas as F  # noqa: E402
from informes import Informe  # noqa: E402
from lector import interpretar  # noqa: E402
from tests.fakes import BASES, FakeNotion  # noqa: E402


def cargar(n, textos, base):
    for t in textos:
        F.guardar_movimiento(n, BASES, interpretar(t, base=base))


class ConTC(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._aj = F.AJUSTES
        F.AJUSTES = Path(self._tmp.name) / "ajustes.json"

    def tearDown(self):
        F.AJUSTES = self._aj
        self._tmp.cleanup()


class Periodos(unittest.TestCase):
    def test_semana_lunes_a_domingo(self):
        p = F.semana(date(2026, 9, 30))   # miercoles
        self.assertEqual((p.desde, p.hasta), (date(2026, 9, 28), date(2026, 10, 4)))
        self.assertEqual(p.clave, "Semana 2026-S40")

    def test_mes(self):
        p = F.mes(date(2026, 2, 10))
        self.assertEqual((p.desde, p.hasta, p.clave), (date(2026, 2, 1), date(2026, 2, 28), "Mes 2026-02"))
        self.assertEqual(F.mes(date(2026, 3, 5)).anterior().desde, date(2026, 2, 1))


class Resumenes(ConTC):
    def test_suma_por_tipo_y_grupo(self):
        n = FakeNotion()
        d = date(2026, 9, 30)
        cargar(n, ["+3000 sueldo", "45 almuerzo", "1200 alquiler", "15 taxi", "ahorro 500 emergencia",
                   "inversion 300 fondo", "10 chocolate"], d)
        r = F.resumir(F.movimientos(n, BASES, d, d), F.dia(d))
        self.assertEqual((r.ingresos, r.gastos, r.ahorro, r.inversion), (3000, 1270, 500, 300))
        self.assertEqual(r.balance, 1730)
        self.assertAlmostEqual(r.tasa_ahorro, 1730 / 3000)
        self.assertEqual(r.necesidades, 1215)
        self.assertEqual(r.deseos, 55)
        self.assertEqual((r.hormiga_n, r.hormiga), (2, 25))

    def test_dolares_se_convierten(self):
        n = FakeNotion()
        F.fijar_tipo_de_cambio("USD", 3.70)
        F.guardar_movimiento(n, BASES, interpretar("+100 usd facebook", base=date(2026, 9, 1)))
        f = n.dbs["db-mov"][0]
        self.assertEqual((f["Monto"], f["Moneda"], f["Tipo de cambio"], f["Monto S/"]), (100, "USD", 3.7, 370))

    def test_filtra_por_fechas(self):
        n = FakeNotion()
        cargar(n, ["10 taxi"], date(2026, 9, 29))
        cargar(n, ["20 taxi"], date(2026, 9, 30))
        self.assertEqual(len(F.movimientos(n, BASES, date(2026, 9, 30), date(2026, 9, 30))), 1)


class Presupuesto(ConTC):
    def test_fijar_reescribe(self):
        n = FakeNotion()
        F.fijar_presupuesto(n, BASES, "Movilidad", 300)
        F.fijar_presupuesto(n, BASES, "Movilidad", 250)
        self.assertEqual(F.presupuesto(n, BASES), {"Movilidad": 250})

    def test_estado_ordena_lo_pasado_primero(self):
        est = F.estado_presupuesto({"A": 120, "B": 10, "C": 5}, {"A": 100, "B": 100}, 0.5)
        self.assertEqual([e[0] for e in est], ["A", "B", "C"])
        self.assertIsNone(est[2][3])


class Patrimonio(ConTC):
    def test_neto_y_liquidez(self):
        n = FakeNotion()
        F.fijar_tipo_de_cambio("USD", 4.0)
        F.fijar_patrimonio(n, BASES, "Interbank", "Activo", "Efectivo y bancos", 5000)
        F.fijar_patrimonio(n, BASES, "Binance", "Activo", "Cripto", 100, "USD")
        _, antes = F.fijar_patrimonio(n, BASES, "Interbank", "Activo", "Efectivo y bancos", 6000)
        F.fijar_patrimonio(n, BASES, "Ripley", "Pasivo", "Tarjeta de crédito", 1000)
        self.assertEqual(antes, 5000)
        self.assertEqual(F.neto(F.patrimonio(n, BASES)), (6400, 1000, 5400, 6000))


class Metas(ConTC):
    def test_crear_y_sumar(self):
        n = FakeNotion()
        F.fijar_meta(n, BASES, "Fondo de emergencia", 20000)
        m = F.buscar_meta(F.metas(n, BASES), "emergencia")
        self.assertEqual(F.sumar_a_meta(n, m, 500), 500)
        self.assertEqual(F.metas(n, BASES)[0]["ahorrado"], 500)


class Consejos(unittest.TestCase):
    def _r(self, ingresos, movs):
        r = F.Resumen(F.mes(date(2026, 9, 1)), ingresos=ingresos)
        for cat, v in movs:
            r.gastos += v
            r.por_categoria[cat] = r.por_categoria.get(cat, 0) + v
            if F.C.grupo(cat) == "Necesidad":
                r.necesidades += v
            else:
                r.deseos += v
        return r

    def test_gasta_mas_de_lo_que_gana(self):
        c = F.consejos(self._r(1000, [("Vivienda", 1200)]))
        self.assertTrue(c[0].startswith("🔴"))

    def test_deseos_sobre_30(self):
        c = F.consejos(self._r(1000, [("Comida y restaurantes", 400)]))
        self.assertTrue(any("30%" in x for x in c))

    def test_presupuesto_pasado_va_primero(self):
        c = F.consejos(self._r(5000, [("Movilidad", 400)]), {"Movilidad": 300})
        self.assertIn("Pasaste el presupuesto", c[0])

    def test_fondo_de_emergencia_y_tarjeta(self):
        items = [{"clase": "Activo", "tipo": "Efectivo y bancos", "valor_s": 2000},
                 {"clase": "Pasivo", "tipo": "Tarjeta de crédito", "valor_s": 800}]
        c = F.consejos(self._r(5000, [("Vivienda", 1000)]), {}, items, gasto_mensual=2000)
        self.assertTrue(any("1.0 meses" in x for x in c))
        self.assertTrue(any("tarjetas" in x for x in c))


class InformeCompleto(ConTC):
    def test_semanal_texto_y_notion(self):
        n = FakeNotion()
        d = date(2026, 9, 30)
        cargar(n, ["+4000 sueldo", "60 almuerzo", "25 taxi"], d)
        cargar(n, ["50 almuerzo"], date(2026, 9, 22))   # semana anterior
        F.fijar_presupuesto(n, BASES, "Comida y restaurantes", 100)
        inf = Informe(n, BASES, F.semana(d), dia_de_corte=d)
        t = inf.texto()
        self.assertIn("S/ 85.00", t)
        self.assertIn("▲ 70%", t)          # 85 contra 50
        self.assertIn("Pasaste el presupuesto", t)   # comida del mes: 110 de 100
        inf.guardar()
        inf.guardar()                      # la segunda vez reescribe, no duplica
        filas = n.dbs["db-res"]
        self.assertEqual(len(filas), 1)
        self.assertEqual((filas[0]["Periodo"], filas[0]["Gastos S/"], filas[0]["Ingresos S/"]), ("Semana 2026-S40", 85, 4000))


if __name__ == "__main__":
    unittest.main()


class TipoDeCambioAutomatico(unittest.TestCase):
    """El del dia se baja de internet (aca simulado); a mano manda; sin internet queda el de respaldo."""

    def setUp(self):
        import config
        self._tmp = tempfile.TemporaryDirectory()
        self._aj, self._auto, self._get = F.AJUSTES, config.TC_AUTO, F.requests.get
        F.AJUSTES = Path(self._tmp.name) / "ajustes.json"
        config.TC_AUTO = True
        self.llamadas = []

    def tearDown(self):
        import config
        F.AJUSTES, config.TC_AUTO, F.requests.get = self._aj, self._auto, self._get
        self._tmp.cleanup()

    def internet(self, *respuestas):
        """Cada llamada a requests.get devuelve la siguiente respuesta (un dict, o una excepcion)."""
        cola = list(respuestas)

        class R:
            def __init__(self, j):
                self.j = j

            def raise_for_status(self):
                pass

            def json(self):
                return self.j

        def get(url, timeout=None):
            self.llamadas.append(url)
            r = cola.pop(0)
            if isinstance(r, Exception):
                raise r
            return R(r)
        F.requests.get = get

    def test_baja_el_del_dia_y_lo_guarda_6_horas(self):
        self.internet({"rates": {"PEN": 3.38, "EUR": 0.85, "RUB": 79.0}})
        self.assertEqual(F.tipo_de_cambio("USD"), 3.38)
        self.assertAlmostEqual(F.tipo_de_cambio("RUB"), 3.38 / 79, places=5)
        self.assertAlmostEqual(F.tipo_de_cambio("EUR"), round(3.38 / 0.85, 4))
        F.soles(100, "USD")
        self.assertEqual(len(self.llamadas), 1)          # no vuelve a internet en cada calculo

    def test_segunda_fuente_si_la_primera_falla(self):
        self.internet(F.requests.ConnectionError(), {"usd": {"pen": 3.5, "eur": 0.9, "rub": 80}})
        self.assertEqual(F.tipo_de_cambio("USD"), 3.5)
        self.assertEqual(len(self.llamadas), 2)

    def test_sin_internet_usa_el_de_respaldo_y_no_insiste(self):
        self.internet(F.requests.ConnectionError(), F.requests.Timeout())
        self.assertEqual(F.tipo_de_cambio("USD"), F.TC_USD)
        F.tipo_de_cambio("RUB")
        self.assertEqual(len(self.llamadas), 2)          # no reintenta antes de 30 minutos

    def test_datos_absurdos_se_descartan(self):
        self.internet({"rates": {"PEN": 0, "EUR": 0.9, "RUB": 80}}, {"usd": {"pen": 3.4, "eur": 0.9, "rub": 80000}})
        self.assertEqual(F.tipo_de_cambio("USD"), F.TC_USD)

    def test_el_intento_queda_anotado_antes_de_salir_a_internet(self):
        """Si la fuente cuelga y el servicio se reinicia en ese rato, no se vuelve a colgar."""
        def se_corta(url, timeout=None):
            self.llamadas.append(url)
            raise KeyboardInterrupt()          # como si systemd matara el proceso mientras bajaba
        F.requests.get = se_corta
        with self.assertRaises(KeyboardInterrupt):
            F.tipo_de_cambio("USD")
        self.assertIn("intento_tc", json.loads(F.AJUSTES.read_text()))

        # el servicio arranca de nuevo y lee el mismo ajustes.json: no reintenta antes de 30 minutos
        self.internet({"rates": {"PEN": 3.38, "EUR": 0.85, "RUB": 79.0}})
        self.llamadas.clear()
        self.assertEqual(F.tipo_de_cambio("USD"), F.TC_USD)
        self.assertEqual(self.llamadas, [])

    def test_a_mano_manda_y_auto_lo_quita(self):
        self.internet({"rates": {"PEN": 3.38, "EUR": 0.85, "RUB": 79.0}}, {"rates": {"PEN": 3.40, "EUR": 0.85, "RUB": 79.0}})
        F.fijar_tipo_de_cambio("USD", 3.5)
        self.assertEqual(F.tipo_de_cambio("USD"), 3.5)
        self.assertAlmostEqual(F.tipo_de_cambio("RUB"), 3.38 / 79, places=5)   # el rublo sigue automatico
        F.tc_a_automatico()
        self.assertEqual(F.tipo_de_cambio("USD"), 3.40)  # vuelve a bajarlo al momento


class CompararMeses(ConTC):
    """Con fechas fijas, para que no dependa de qué día es hoy."""

    def setUp(self):
        super().setUp()
        self.n = FakeNotion()
        # mayo: el 5 y el 25 ; junio: el 5
        cargar(self.n, ["200 supermercado 5/5", "500 supermercado 25/5", "100 taxi 5/5"], date(2026, 6, 10))
        cargar(self.n, ["300 supermercado 5/6", "120 dentista 5/6"], date(2026, 6, 10))

    def test_corta_los_dos_meses_el_mismo_dia(self):
        c = F.comparar_meses(self.n, BASES, date(2026, 6, 10))
        self.assertEqual((c["dia"], c["completo"]), (10, False))
        self.assertEqual(c["a"].gastos, 420)            # junio: 300 + 120
        self.assertEqual(c["b"].gastos, 300)            # mayo hasta el 10: 200 + 100, no los 500 del 25
        porcat = {x["categoria"]: x for x in c["cambios"]}
        self.assertEqual((porcat["Supermercado"]["ahora"], porcat["Supermercado"]["antes"]), (300, 200))
        self.assertEqual(porcat["Supermercado"]["pct"], 0.5)
        self.assertEqual((porcat["Citas médicas"]["antes"], porcat["Citas médicas"]["pct"]), (0, None))
        self.assertEqual((porcat["Movilidad"]["ahora"], porcat["Movilidad"]["antes"]), (0, 100))

    def test_mes_entero_contra_mes_entero(self):
        c = F.comparar_meses(self.n, BASES, date(2026, 6, 30))
        self.assertEqual((c["dia"], c["completo"]), (30, True))
        self.assertEqual(c["b"].gastos, 800)            # mayo entero: 200 + 500 + 100
        self.assertEqual(c["cambios"][0]["categoria"], "Supermercado")   # el que más cambió, primero

    def test_febrero_contra_enero_sin_dia_31(self):
        cargar(self.n, ["90 cine 31/1"], date(2026, 2, 28))
        c = F.comparar_meses(self.n, BASES, date(2026, 2, 28))
        self.assertEqual(c["dia"], 28)                  # enero tiene 31, pero se corta el 28
        self.assertEqual(c["b"].gastos, 0)              # el cine del 31 de enero queda fuera
