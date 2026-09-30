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
        self.toca("Transporte")
        self.assertEqual(self.movs[0]["Categoría"], "Transporte")
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
