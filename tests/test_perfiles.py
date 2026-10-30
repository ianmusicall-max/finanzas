"""Contrato que todo perfil tiene que cumplir.

Los datos personales (categorias, bancos, alias) viven en `perfiles/<nombre>.py` y la logica en
`categorias.py`. Si un perfil nombra algo que no existe, el bot no se cae: escribe en Notion una
categoria inventada o una comparacion nunca da verdadero, y eso se descubre semanas despues con
los numeros ya mal. Estos tests corren sobre *todos* los perfiles, asi que un perfil nuevo queda
cubierto por el solo hecho de existir.
"""

import importlib
import pkgutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import perfiles  # noqa: E402

TIPOS = ["Gasto", "Ingreso", "Ahorro", "Inversión"]
GRUPOS = ["Necesidad", "Deseo"]

NOMBRES = sorted(m.name for m in pkgutil.iter_modules(perfiles.__path__))


def cargar(nombre):
    return importlib.import_module("perfiles.%s" % nombre)


class Perfiles(unittest.TestCase):

    def test_hay_perfiles(self):
        self.assertIn("jose", NOMBRES)
        self.assertIn("daria", NOMBRES)

    def test_el_catch_all_de_cada_tipo_existe_de_verdad(self):
        """`C.otros(tipo)` y el respaldo de `finanzas` escriben este nombre en Notion."""
        for nombre in NOMBRES:
            p = cargar(nombre)
            tablas = {"Gasto": p.GASTOS, "Ingreso": p.INGRESOS,
                      "Ahorro": p.AHORROS, "Inversión": p.INVERSIONES}
            for tipo in TIPOS:
                with self.subTest(perfil=nombre, tipo=tipo):
                    self.assertIn(p.OTROS[tipo], tablas[tipo])

    def test_retiro_de_ahorro_es_una_categoria_de_ingreso(self):
        """Si no, el bot le ofrece apartar ahorro del propio retiro del ahorro."""
        for nombre in NOMBRES:
            p = cargar(nombre)
            with self.subTest(perfil=nombre):
                self.assertIn(p.RETIRO_AHORRO, p.INGRESOS)

    def test_los_grupos_de_gasto_son_validos(self):
        for nombre in NOMBRES:
            p = cargar(nombre)
            for cat, info in p.GASTOS.items():
                with self.subTest(perfil=nombre, categoria=cat):
                    self.assertIn(info[0], GRUPOS)
                    self.assertTrue(info[1], "le falta el emoji")
                    self.assertIsInstance(info[2], list)

    def test_las_categorias_fijas_existen(self):
        for nombre in NOMBRES:
            p = cargar(nombre)
            for cat in p.CATEGORIAS_FIJAS:
                with self.subTest(perfil=nombre, categoria=cat):
                    self.assertIn(cat, p.GASTOS)

    def test_las_tarjetas_y_billeteras_son_medios_de_pago(self):
        for nombre in NOMBRES:
            p = cargar(nombre)
            for medio in list(p.TARJETAS) + list(p.BILLETERA_BANCO):
                with self.subTest(perfil=nombre, medio=medio):
                    self.assertIn(medio, p.MEDIOS)

    def test_las_billeteras_descuentan_de_un_medio_que_existe(self):
        for nombre in NOMBRES:
            p = cargar(nombre)
            for billetera, banco in p.BILLETERA_BANCO.items():
                with self.subTest(perfil=nombre, billetera=billetera):
                    self.assertIn(banco, p.MEDIOS)

    def test_los_alias_apuntan_a_medios_que_existen(self):
        for nombre in NOMBRES:
            p = cargar(nombre)
            for alias, medio in p.ALIAS_MEDIOS.items():
                with self.subTest(perfil=nombre, alias=alias):
                    self.assertIn(medio, p.MEDIOS)

    def test_la_moneda_base_es_la_primera_de_la_lista(self):
        """La primera de MONEDAS es la moneda en la que se suma todo."""
        for nombre in NOMBRES:
            p = cargar(nombre)
            with self.subTest(perfil=nombre):
                self.assertTrue(p.MONEDAS)
                self.assertIn(p.MONEDAS[0], ("PEN", "RUB", "USD", "EUR"))

    def test_lo_renombrado_apunta_a_una_categoria_que_existe(self):
        for nombre in NOMBRES:
            p = cargar(nombre)
            for viejo, ahora in p.RENOMBRADAS.items():
                with self.subTest(perfil=nombre, viejo=viejo):
                    self.assertIn(ahora, p.GASTOS)
