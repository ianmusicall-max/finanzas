import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import finanzas as F  # noqa: E402
from bot import Bot, codigo_salida, leer_patrimonio  # noqa: E402
from telegram import TelegramError  # noqa: E402
from tests.fakes import BASES, FakeNotion, FakeTelegram  # noqa: E402

YO = 7


def mensaje(texto, user=YO, chat=YO, tipo="private"):
    return {"update_id": 1, "message": {"chat": {"id": chat, "type": tipo}, "from": {"id": user}, "text": texto}}


def boton(data, user=YO, chat=YO):
    return {"update_id": 2, "callback_query": {"id": "cb", "from": {"id": user}, "data": data,
                                               "message": {"chat": {"id": chat, "type": "private"}, "message_id": 9}}}


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._aj = F.AJUSTES
        F.AJUSTES = Path(self._tmp.name) / "ajustes.json"
        self.tg, self.n = FakeTelegram(), FakeNotion()
        self.bot = Bot(self.tg, self.n, BASES, {YO})

    def tearDown(self):
        F.AJUSTES = self._aj
        self._tmp.cleanup()

    def di(self, texto):
        self.bot.procesar(mensaje(texto))
        return self.tg.ultimo

    def toca(self, etiqueta):
        self.bot.procesar(boton(self.tg.data_de(etiqueta)))
        return self.tg.ultimo

    @property
    def movs(self):
        return self.n.dbs["db-mov"]


class Autorizacion(Base):
    def test_sin_usuarios_dice_el_id(self):
        b = Bot(self.tg, self.n, BASES, set())
        b.procesar(mensaje("45 almuerzo", user=555, chat=555))
        self.assertIn("555", self.tg.ultimo)
        self.assertEqual(self.movs, [])

    def test_extrano_una_sola_vez(self):
        self.bot.procesar(mensaje("hola", user=9, chat=9))
        self.bot.procesar(mensaje("hola", user=9, chat=9))
        self.assertEqual(len(self.tg.enviados), 1)

    def test_grupos_se_ignoran(self):
        self.bot.procesar(mensaje("45 almuerzo", tipo="group"))
        self.assertEqual(self.tg.enviados, [])


class Anotar(Base):
    def test_gasto_queda_en_notion(self):
        t = self.di("45 almuerzo interbank")
        self.assertIn("Comida y restaurantes", t)
        self.assertIn("S/ 45.00", t)
        f = self.movs[0]
        self.assertEqual((f["Tipo"], f["Monto S/"], f["Medio de pago"], f["Grupo"], f["Origen"]),
                         ("Gasto", 45, "Interbank", "Deseo", "Telegram"))

    def test_categoria_desconocida_pregunta(self):
        self.di("80 cosas raras")
        self.toca("Movilidad")
        self.assertEqual(self.movs[0]["Categoría"], "Movilidad")
        self.assertEqual(self.movs[0]["Grupo"], "Necesidad")

    def test_cambiar_categoria(self):
        self.di("30 uber")
        self.toca("Cambiar categoría")
        self.toca("Viajes")
        self.assertEqual(self.movs[0]["Categoría"], "Viajes")

    def test_deshacer_con_boton_y_comando(self):
        self.di("30 uber")
        self.toca("Deshacer")
        self.assertEqual(self.movs, [])
        self.di("20 taxi")
        self.di("/deshacer")
        self.assertEqual(self.movs, [])
        self.assertIn("No hay nada", self.di("/deshacer"))

    def test_no_entendi(self):
        self.assertIn("No encontré el monto", self.di("almuerzo"))
        self.assertEqual(self.movs, [])

    def test_comando_forzado(self):
        self.di("/ingreso 200 regalo")
        self.assertEqual(self.movs[0]["Tipo"], "Ingreso")

    def test_dolares_muestra_conversion(self):
        self.di("/tc 3.70")
        t = self.di("+100 usd facebook")
        self.assertIn("USD 100.00 = S/ 370.00", t)


class AhorroYMetas(Base):
    def test_ahorro_suma_a_la_meta_y_se_deshace(self):
        self.di("/meta Fondo de emergencia 20000")
        t = self.di("ahorro 500 emergencia")
        self.assertIn("S/ 500.00 de S/ 20,000.00", t)
        self.assertEqual(self.n.dbs["db-met"][0]["Ahorrado S/"], 500)
        self.toca("Deshacer")
        self.assertEqual(self.n.dbs["db-met"][0]["Ahorrado S/"], 0)

    def test_metas_lista(self):
        self.di("/meta Auto 100k")
        self.assertIn("S/ 100,000.00", self.di("/metas"))


class Presupuesto(Base):
    def test_fijar_y_avisar(self):
        self.assertIn("S/ 100.00 al mes", self.di("/presupuesto comida 100"))
        self.assertIn("🟡", self.di("85 almuerzo"))
        self.assertIn("Pasaste el presupuesto", self.di("20 cafe"))
        t = self.di("/presupuesto")
        self.assertIn("🔴 Comida y restaurantes", t)

    def test_categoria_invalida(self):
        self.assertIn("No reconozco", self.di("/presupuesto zzz 100"))


class Patrimonio(Base):
    def test_activos_y_deudas(self):
        self.di("/activo Interbank 5200")
        self.di("/deuda Tarjeta Ripley 1200")
        t = self.di("/activo Interbank 6000")
        self.assertIn("antes S/ 5,200.00", t)
        self.assertIn("Patrimonio neto: <b>S/ 4,800.00</b>", t)
        self.assertIn("Lo que debes", self.di("/patrimonio"))

    def test_leer_patrimonio(self):
        self.assertEqual(leer_patrimonio("Activo", "Binance 800 usd"), ("Binance", 800, "USD", "Cripto"))
        self.assertEqual(leer_patrimonio("Activo", "Auto 45000"), ("Auto", 45000, "PEN", "Vehículo"))
        self.assertEqual(leer_patrimonio("Pasivo", "Tarjeta Ripley 1,200"), ("Tarjeta Ripley", 1200, "PEN", "Tarjeta de crédito"))


class Deudas(Base):
    @property
    def deudas(self):
        return self.n.dbs["db-deu"]

    def test_deuda_va_a_la_base_deudas(self):
        t = self.di("/deuda Tarjeta Ripley 1200")
        self.assertIn("Total de deudas: <b>S/ 1,200.00</b>", t)
        d = self.deudas[0]
        self.assertEqual((d["Deuda"], d["Tipo"], d["Saldo"], d["Monto original"], d["Estado"]),
                         ("Tarjeta Ripley", "Tarjeta de crédito", 1200, 1200, "Activa"))
        self.assertEqual(self.n.dbs["db-pat"], [])
        t = self.di("/deuda Tarjeta Ripley 1500")
        self.assertIn("antes S/ 1,200.00", t)
        self.assertEqual(len(self.deudas), 1)

    def test_cuenta_en_el_patrimonio_neto(self):
        self.di("/activo Interbank 5200")
        self.di("/deuda Préstamo BCP 2000")
        t = self.di("/patrimonio")
        self.assertIn("Patrimonio neto: S/ 3,200.00", t)
        self.assertIn("Préstamo BCP", t)

    def test_pago_baja_el_saldo_hasta_pagarla(self):
        self.di("/deuda Tarjeta Ripley 1000")
        t = self.di("/pago ripley 300")
        self.assertIn("Te queda: <b>S/ 700.00</b>", t)
        self.assertEqual(self.deudas[0]["Saldo"], 700)
        self.assertEqual(self.movs, [])  # pagar una deuda no es un gasto nuevo
        t = self.di("/pago ripley 700")
        self.assertIn("pagada por completo", t)
        self.assertEqual(self.deudas[0]["Estado"], "Pagada")
        self.assertIn("No tienes deudas activas", self.di("/deudas"))

    def test_pago_en_otra_moneda(self):
        F.fijar_tipo_de_cambio("USD", 4.0)
        self.di("/deuda Juan 100 usd")
        self.assertEqual(self.deudas[0]["Tipo"], "Otra")
        self.di("/pago juan 200 soles")
        self.assertEqual(self.deudas[0]["Saldo"], 50)

    def test_lista_y_errores(self):
        self.di("/deuda Tarjeta Ripley 1200")
        self.di("/deuda Préstamo BCP 15000")
        self.n.dbs["db-deu"][1].update({"Tasa anual": 0.18, "Cuota mensual": 800, "Día de pago": 5})
        t = self.di("/deudas")
        self.assertIn("Deudas: S/ 16,200.00", t)
        self.assertLess(t.index("Préstamo BCP"), t.index("Tarjeta Ripley"))
        self.assertIn("tasa 18%", t)
        self.assertIn("Cuotas al mes: S/ 800.00", t)
        self.assertIn("No encuentro", self.di("/pago visa 10"))
        self.assertIn("Tus deudas", self.di("/pago"))
        self.assertIn("Escribe el nombre", self.di("/deuda"))

    def test_avalancha_en_consejos(self):
        self.di("/deuda Tarjeta Ripley 1200")
        self.di("/deuda Préstamo BCP 15000")
        self.n.dbs["db-deu"][0]["Tasa anual"] = 0.65
        self.n.dbs["db-deu"][1]["Tasa anual"] = 0.18
        self.di("+3000 sueldo")
        self.assertIn("avalancha: paga el mínimo en todas y lo extra a Tarjeta Ripley", self.di("/consejos"))

    def test_sin_base_deudas_sigue_en_patrimonio(self):
        bases = {k: v for k, v in self.bot.bases.items() if k != "Deudas"}
        b = Bot(self.tg, self.n, bases, {YO})
        b.procesar(mensaje("/deuda Tarjeta Ripley 1200"))
        self.assertEqual(self.n.dbs["db-pat"][0]["Clase"], "Pasivo")

    def test_menu_tiene_deudas(self):
        self.di("/start")
        self.assertIn("No tienes deudas activas", self.toca("Deudas"))


class Resumenes(Base):
    def test_hoy_semana_mes(self):
        self.di("+3000 sueldo")
        self.di("45 almuerzo")
        self.assertIn("S/ 45.00", self.di("/hoy"))
        self.assertIn("Gastos: <b>S/ 45.00</b>", self.di("/semana"))
        self.assertIn("tasa de ahorro 98%", self.di("/mes"))
        self.bot.procesar(boton("m:presupuesto"))
        self.assertIn("Presupuesto", self.tg.ultimo)

    def test_consejos_y_metodos(self):
        self.di("+1000 sueldo")
        self.di("1200 alquiler")
        self.assertIn("🔴", self.di("/consejos"))
        self.assertIn("50/30/20", self.di("/metodos"))

    def test_ultimos(self):
        self.di("45 almuerzo")
        self.di("12 taxi")
        t = self.di("/ultimos")
        self.assertLess(t.index("Taxi"), t.index("Almuerzo"))


class Salida(unittest.TestCase):
    def test_codigos(self):
        self.assertEqual(codigo_salida(TelegramError("x", 401)), 2)
        self.assertEqual(codigo_salida(TelegramError("x", 409)), 3)
        self.assertEqual(codigo_salida(TelegramError("x", 500)), 1)


if __name__ == "__main__":
    unittest.main()


class Formularios(Base):
    def setUp(self):
        super().setUp()
        import formularios
        self._fa = formularios.AJUSTES
        formularios.AJUSTES = F.AJUSTES

    def tearDown(self):
        import formularios
        formularios.AJUSTES = self._fa
        super().tearDown()

    def test_gasto_completo_como_el_google_form(self):
        self.di("/gasto")
        self.assertIn("Nuevo gasto", self.tg.enviados[-2][1])
        self.assertIn("¿Qué fecha?", self.tg.ultimo)
        self.toca("Ayer")
        self.assertIn("cuenta", self.tg.ultimo)
        self.toca("Salud")
        self.toca("Tinkoff")
        self.toca("Medicina")
        self.toca("RUB")
        self.assertIn("descripción", self.tg.ultimo)
        self.di("pastillas para la gripe")
        self.assertIn("¿Cuánto fue?", self.tg.ultimo)
        self.assertIn("número", self.di("mucho"))
        t = self.di("1.250,50")
        self.assertIn("revisa antes de guardar", t)
        self.assertIn("RUB 1,250.50", t)
        self.assertEqual(self.movs, [])          # nada se guarda sin tocar Guardar
        self.toca("Guardar")
        f = self.movs[0]
        self.assertEqual((f["Tipo"], f["Cuenta"], f["Medio de pago"], f["Categoría"], f["Moneda"], f["Monto"], f["Descripción"]),
                         ("Gasto", "Salud", "Tinkoff", "Medicina", "RUB", 1250.5, "Pastillas para la gripe"))
        self.assertEqual(f["Fecha"], (F.hoy() - F.timedelta(days=1)).isoformat())
        self.assertAlmostEqual(f["Monto S/"], round(1250.5 * F.tipo_de_cambio("RUB"), 2))
        self.assertIn("cuenta Salud", self.tg.ultimo)

    def test_corregir_antes_de_guardar(self):
        self.di("/gasto")
        for b in ("Hoy", "Gastos", "Interbank", "Supermercado", "PEN"):
            self.toca(b)
        self.toca("Omitir")
        self.di("80")
        self.toca("Corregir")
        self.toca("Importe")
        t = self.di("85")
        self.assertIn("PEN 85.00", t)            # vuelve directo al resumen
        self.toca("Guardar")
        self.assertEqual((self.movs[0]["Monto"], self.movs[0]["Descripción"]), (85, "Supermercado"))

    def test_lo_ultimo_elegido_sale_primero(self):
        self.di("/gasto")
        self.toca("Hoy")
        self.toca("Gastos")
        self.toca("Ripley")
        self.toca("Cancelar")
        self.di("/gasto")
        self.toca("Hoy")
        self.toca("Gastos")
        self.assertTrue(self.tg.botones()[0][0].startswith("Ripley"))

    def test_ingreso_y_fecha_escrita(self):
        self.di("/ingreso")
        self.di("15/09")
        self.toca("PayPal")
        self.toca("Facebook")
        self.toca("USD")
        self.di("pago de septiembre")
        self.di("1943")
        self.toca("Guardar")
        f = self.movs[0]
        self.assertEqual((f["Tipo"], f["Categoría"], f["Medio de pago"], f["Moneda"], f["Fecha"][5:]),
                         ("Ingreso", "Facebook", "PayPal", "USD", "09-15"))

    def test_ahorro_a_una_meta(self):
        self.di("/meta Fondo de emergencia 20000")
        self.di("/ahorro")
        self.toca("Hoy")
        self.toca("Fondo de emergencia")
        self.toca("Interbank")
        self.toca("PEN")
        self.di("500")
        self.toca("Guardar")
        self.assertEqual(self.n.dbs["db-met"][0]["Ahorrado S/"], 500)
        self.assertEqual(self.movs[0]["Categoría"], "Fondo de emergencia")

    def test_cancelar_y_boton_viejo(self):
        self.di("/gasto")
        viejo = self.tg.data_de("Hoy")
        self.toca("Hoy")
        self.bot.procesar(boton(viejo))
        self.assertIn("pregunta anterior", self.tg.enviados[-2][1])
        self.di("/cancelar")
        self.assertIn("Cancelado", self.tg.ultimo)
        self.assertEqual(self.movs, [])

    def test_cuenta_inversion_no_es_gasto(self):
        self.di("/gasto")
        for b in ("Hoy", "Inversión", "Interbank", "Vivienda", "PEN"):
            self.toca(b)
        self.di("autovaluo depa")
        self.di("2174")
        self.toca("Guardar")
        m = F.mes()
        r = F.resumir(F.movimientos(self.n, BASES, m.desde, m.hasta), m)
        self.assertEqual((r.gastos, r.inversion), (0, 2174))

    def test_menu_tiene_los_formularios(self):
        self.di("/start")
        self.bot.procesar(boton(self.tg.data_de("Gasto")))
        self.assertIn("¿Qué fecha?", self.tg.ultimo)
