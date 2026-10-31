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


class MonedaBase(unittest.TestCase):
    """Las columnas de Notion llevan el simbolo de la moneda base en el nombre.

    El sistema de José suma en soles ("Monto S/") y el de Дарья en rublos ("Monto ₽"). Si alguien
    vuelve a escribir la moneda a mano en el codigo, el clon en rublos crea columnas con el nombre
    equivocado y no se nota hasta que los numeros ya estan en Notion.
    """

    def test_el_sufijo_sale_de_la_moneda_base(self):
        import config
        viejo = config.SUFIJO
        self.addCleanup(setattr, config, "SUFIJO", viejo)
        config.SUFIJO = "₽"
        self.assertEqual(config.columna("Monto"), "Monto ₽")
        self.assertEqual(config.columna("Patrimonio neto"), "Patrimonio neto ₽")

    def test_por_defecto_sigue_siendo_soles(self):
        """La instalación de siempre no puede cambiar de columnas sola."""
        import config
        self.assertEqual(config.MONEDA_BASE, "PEN")
        self.assertEqual(config.columna("Monto"), "Monto S/")

    def test_no_queda_ninguna_columna_con_la_moneda_escrita_a_mano(self):
        import re
        raiz = Path(__file__).resolve().parents[1]
        patron = re.compile(r'"(Monto|Saldo|Valor|Ahorrado|Ahorro|Objetivo|Mensual|Anual|Balance'
                            r'|Ingresos|Gastos|Inversión|Por mes|Patrimonio neto) S/"')
        culpables = []
        for nombre in ("notion.py", "finanzas.py", "informes.py", "excel.py", "bot.py", "importar_hoja.py"):
            for i, linea in enumerate((raiz / nombre).read_text(encoding="utf-8").splitlines(), 1):
                if patron.search(linea):
                    culpables.append("%s:%d" % (nombre, i))
        self.assertEqual(culpables, [], "usá columna(...) en vez de escribir la moneda a mano")


class ZonaHoraria(unittest.TestCase):
    """El corte del día y la hora de los resúmenes salen de ZONA_HORARIA.

    Sin tzdata a propósito: ni Lima ni Moscú tienen horario de verano, así que el desfase fijo
    alcanza y el servidor no necesita paquetes extra.
    """

    def test_las_zonas_conocidas(self):
        import config
        self.assertEqual(config._desfase("America/Lima"), -5)
        self.assertEqual(config._desfase("Europe/Moscow"), 3)

    def test_se_puede_poner_el_desfase_a_mano(self):
        import config
        self.assertEqual(config._desfase("UTC+3"), 3)
        self.assertEqual(config._desfase("-5"), -5)
        self.assertEqual(config._desfase("UTC+5:30"), 5.5)

    def test_una_zona_que_no_se_entiende_avisa_claro(self):
        """Mejor que no arranque, a que el resumen salga a cualquier hora sin que nadie lo note."""
        import config
        with self.assertRaises(SystemExit) as e:
            config._desfase("Marte/Olympus")
        self.assertIn("ZONA_HORARIA", str(e.exception))

    def test_por_defecto_sigue_siendo_lima(self):
        import config
        self.assertEqual(config.ZONA_HORARIA, "America/Lima")
