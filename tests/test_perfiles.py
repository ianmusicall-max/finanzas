"""Contrato que todo perfil tiene que cumplir.

Los datos personales (categorias, bancos, alias) viven en `perfiles/<nombre>.py` y la logica en
`categorias.py`. Si un perfil nombra algo que no existe, el bot no se cae: escribe en Notion una
categoria inventada o una comparacion nunca da verdadero, y eso se descubre semanas despues con
los numeros ya mal. Estos tests corren sobre *todos* los perfiles, asi que un perfil nuevo queda
cubierto por el solo hecho de existir.
"""

import importlib
import os
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

    @unittest.skipIf(os.environ.get("MONEDA_BASE"), "el .env fija otra moneda base")
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

    @unittest.skipIf(os.environ.get("ZONA_HORARIA"), "el .env fija otra zona")
    def test_por_defecto_sigue_siendo_lima(self):
        import config
        self.assertEqual(config.ZONA_HORARIA, "America/Lima")


class FormulaDeMetas(unittest.TestCase):
    """La base Metas tiene una fórmula de Notion que nombra dos columnas.

    Esos nombres llevan la moneda, así que hay que interpolarlos. Si queda el texto literal
    `prop(columna("Objetivo"))`, Notion contesta "Type error with formula" y la base no se crea
    — y las tres anteriores sí, así que parece que todo anduvo hasta que falta una.
    """

    def _expresion(self):
        import notion
        esq = notion.esquemas()[notion.METAS]
        return esq[notion.n_prop("Avance")]["formula"]["expression"]

    def test_la_formula_nombra_las_columnas_de_verdad(self):
        import notion
        from config import columna
        e = self._expresion()
        # Con el nombre que tienen en Notion: la formula las nombra dentro de un texto, asi que
        # no la alcanza la traduccion de las llaves del esquema.
        self.assertIn('prop("%s")' % notion.n_prop(columna("Objetivo")), e)
        self.assertIn('prop("%s")' % notion.n_prop(columna("Ahorrado")), e)

    def test_no_quedo_la_llamada_sin_evaluar(self):
        self.assertNotIn("columna(", self._expresion())


class ScriptsDeDeploy(unittest.TestCase):
    """Ningún script de deploy puede nombrar a mano la carpeta ni el servicio.

    Los scripts se copian tal cual a las dos instalaciones, así que un `/opt/finanzas` o un
    `finanzas-bot` escrito a mano hace que el sistema del segundo trabaje sobre el del primero.
    Pasó con tres: `actualizar.sh` y `auto-actualizar.sh` hacían `cd /opt/finanzas` (la
    actualización automática de ella entraba a la carpeta de él), y `vigia.sh` ni siquiera leía
    `comun.sh`: vigilaba `finanzas-bot`, lo encontraba vivo y salía contento **sin mirar el bot
    que tenía que cuidar**. Un bot sin vigía y nadie enterándose, que es justo lo que el vigía
    existe para evitar.
    """

    # Los que pueden nombrarlo: el que hace el reemplazo y los instaladores, que dan el valor
    # por defecto de la instalación de siempre.
    PERMITIDOS = {"poner-timers.sh", "instalar-todo.sh", "instalar.sh", "comun.sh"}

    def test_ninguno_nombra_la_carpeta_ni_el_servicio(self):
        raiz = Path(__file__).resolve().parents[1] / "deploy"
        for script in sorted(raiz.glob("*.sh")):
            if script.name in self.PERMITIDOS:
                continue
            for n, linea in enumerate(script.read_text().splitlines(), 1):
                codigo = linea.split("#", 1)[0]
                self.assertNotIn("/opt/finanzas", codigo,
                                 "deploy/%s:%d nombra la carpeta a mano; usa $DIR" % (script.name, n))
                self.assertNotIn("finanzas-", codigo,
                                 "deploy/%s:%d nombra el servicio a mano; usa $SERVICIO-" % (script.name, n))
                self.assertNotIn("-u finanzas", codigo,
                                 "deploy/%s:%d nombra el usuario a mano; usa $SERVICIO" % (script.name, n))

    def test_los_que_trabajan_leen_comun(self):
        """Quien use $DIR o $SERVICIO tiene que haberlos leído de comun.sh."""
        raiz = Path(__file__).resolve().parents[1] / "deploy"
        for script in sorted(raiz.glob("*.sh")):
            if script.name in ("comun.sh", "instalar-todo.sh"):
                continue
            texto = script.read_text()
            if "$DIR" in texto or "$SERVICIO" in texto:
                self.assertIn("comun.sh", texto,
                              "deploy/%s usa $DIR o $SERVICIO sin leer comun.sh" % script.name)


class MenuPorPerfil(unittest.TestCase):
    """Cada perfil elige qué botones ve; el idioma les pone el nombre.

    `bot.MENU` descarta en silencio una opción sin nombre, así que un botón mal escrito
    simplemente no aparecería y nadie se enteraría. Por eso se comprueba acá.
    """

    def _idiomas(self):
        import importlib
        import pkgutil

        import idiomas
        return {m.name: importlib.import_module("idiomas.%s" % m.name)
                for m in pkgutil.iter_modules(idiomas.__path__)}

    def test_cada_opcion_tiene_nombre_en_todos_los_idiomas(self):
        for nombre in NOMBRES:
            p = cargar(nombre)
            for fila in p.MENU_OPCIONES:
                for opcion in fila:
                    for idioma, mod in self._idiomas().items():
                        with self.subTest(perfil=nombre, opcion=opcion, idioma=idioma):
                            self.assertIn(opcion, mod.BOTONES)

    def test_ningun_boton_repetido_ni_fila_vacia(self):
        for nombre in NOMBRES:
            p = cargar(nombre)
            plano = [op for fila in p.MENU_OPCIONES for op in fila]
            with self.subTest(perfil=nombre):
                self.assertEqual(len(plano), len(set(plano)))
                self.assertTrue(all(fila for fila in p.MENU_OPCIONES))

    def test_todos_los_idiomas_nombran_las_mismas_opciones(self):
        """Si un idioma se queda corto, a esa persona le faltan botones sin aviso."""
        claves = {i: set(m.BOTONES) for i, m in self._idiomas().items()}
        for idioma, k in claves.items():
            with self.subTest(idioma=idioma):
                self.assertEqual(k, claves["es"])

    def test_el_menu_de_daria_deja_fuera_lo_que_no_usa(self):
        """No tiene deudas ni tarjetas de crédito: esos botones solo le ocupan la pantalla."""
        plano = [op for fila in cargar("daria").MENU_OPCIONES for op in fila]
        for opcion in ("deudas", "plan", "patrimonio", "pagos", "proyeccion", "consejos"):
            self.assertNotIn(opcion, plano)
        for opcion in ("gasto", "hoy", "presupuesto", "reloj"):
            self.assertIn(opcion, plano)


class ServiciosDeSystemd(unittest.TestCase):
    """Dos sistemas en el mismo servidor no pueden compartir el nombre de los servicios.

    `deploy/poner-timers.sh` instala los units cambiando cuatro cosas: la carpeta
    (`/opt/finanzas`), el usuario (`User=`/`Group=`), el prefijo (`finanzas-`) y la zona horaria.
    Si un archivo nombra el sistema original de otra forma, esa línea queda apuntando al de José
    y el clon le pisa el bot al dueño — que es exactamente lo que no puede pasar.
    """

    DIRECTIVAS = ("ExecStart", "WorkingDirectory", "ReadWritePaths", "Unit", "User", "Group",
                  "Environment=TZ", "OnCalendar")

    def _units(self):
        return sorted((Path(__file__).resolve().parents[1] / "deploy" / "systemd").glob("finanzas-*"))

    def test_hay_units(self):
        self.assertTrue(self._units(), "no encontré los archivos de systemd")

    def test_lo_que_nombra_el_sistema_lo_cambia_el_instalador(self):
        import re
        cubierto = re.compile(r"/opt/finanzas|^(User|Group)=finanzas$|finanzas-|America/Lima")
        for f in self._units():
            for i, linea in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                linea = linea.strip()
                if linea.startswith("#") or "=" not in linea:
                    continue
                if not linea.startswith(self.DIRECTIVAS):
                    continue
                if ("finanzas" in linea or "America/Lima" in linea) and not cubierto.search(linea):
                    self.fail("%s:%d el instalador no cambiaría esto: %s" % (f.name, i, linea))

    def test_el_instalador_toca_las_cuatro_cosas(self):
        guion = (Path(__file__).resolve().parents[1] / "deploy" / "poner-timers.sh").read_text(encoding="utf-8")
        for pieza in ("/opt/finanzas", "User=finanzas", "Group=finanzas", "finanzas-", "America/Lima"):
            self.assertIn(pieza, guion, "poner-timers.sh ya no reemplaza %r" % pieza)
