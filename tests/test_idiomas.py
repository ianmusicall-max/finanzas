"""Contrato de los idiomas, igual que tests/test_perfiles.py lo es de los perfiles.

El bot traduce buscando la frase en espanol (`idiomas.t`). Eso tiene una virtud y un peligro:
una frase sin traducir **no rompe nada**, sale en espanol. Comodo para traducir de a poco, pero
el que se entera de que falta es el usuario, mirando su telefono.

Por eso estos tests leen el codigo y comprueban, idioma por idioma, que cada `t("...")` del repo
tenga su traduccion. Cuando falte una, el test la nombra entera.
"""
import ast
import importlib
import pathlib
import unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
IDIOMAS = sorted(p.stem for p in (RAIZ / "idiomas").glob("*.py") if not p.stem.startswith("_"))
ORIGEN = "es"   # el idioma en el que esta escrito el codigo

# Frases que llegan a t() dentro de una variable, asi que leyendo el codigo no se ven:
# son los VALORES de las opciones de formularios.py (viajan a Notion, por eso siguen en espanol)
# y lo que se traduce es solo su etiqueta.
POR_VARIABLE = ["Débito", "Crédito", "Un solo pago", "Mensual", "Anual",
                "Sin meta (ahorro general)"]


def frases_del_codigo() -> list:
    """Cada t("...") del repo, en orden de aparicion y sin repetir."""
    out = []
    for f in sorted(RAIZ.glob("*.py")):
        for n in ast.walk(ast.parse(f.read_text())):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "t"
                    and len(n.args) == 1 and isinstance(n.args[0], ast.Constant)
                    and isinstance(n.args[0].value, str) and n.args[0].value not in out):
                out.append(n.args[0].value)
    return out


class TodosLosIdiomas(unittest.TestCase):
    def setUp(self):
        self.frases = frases_del_codigo() + POR_VARIABLE

    def test_hay_frases_que_traducir(self):
        """Si esto da cero es que alguien deshizo los t() sin querer."""
        self.assertGreater(len(self.frases), 40)

    def test_cada_idioma_traduce_todo(self):
        for idioma in IDIOMAS:
            if idioma == ORIGEN:
                continue
            textos = getattr(importlib.import_module("idiomas.%s" % idioma), "TEXTOS", {})
            faltan = [f for f in self.frases if f not in textos]
            self.assertEqual(faltan, [], "\nidiomas/%s.py no traduce %d frase(s):\n%s"
                             % (idioma, len(faltan), "\n".join("  " + repr(f) for f in faltan)))

    def test_no_sobran_traducciones(self):
        """Una frase traducida que ya no esta en el codigo es trabajo perdido y confunde:
        normalmente quiere decir que alguien cambio el texto en espanol y no aca."""
        for idioma in IDIOMAS:
            if idioma == ORIGEN:
                continue
            textos = getattr(importlib.import_module("idiomas.%s" % idioma), "TEXTOS", {})
            sobran = [f for f in textos if f not in self.frases]
            self.assertEqual(sobran, [], "\nidiomas/%s.py traduce frases que ya no existen:\n%s"
                             % (idioma, "\n".join("  " + repr(f) for f in sobran)))

    def test_el_idioma_del_codigo_no_traduce_nada(self):
        textos = getattr(importlib.import_module("idiomas.%s" % ORIGEN), "TEXTOS", {})
        self.assertEqual(textos, {}, "idiomas/%s.py es el idioma del codigo: no traduce" % ORIGEN)

    def test_los_mismos_nombres_en_todos(self):
        """Un idioma al que le falte una constante tumbaria el bot al arrancar."""
        esperado = None
        for idioma in IDIOMAS:
            m = importlib.import_module("idiomas.%s" % idioma)
            nombres = {n for n in vars(m) if n.isupper()}
            if esperado is None:
                esperado = (idioma, nombres)
            self.assertEqual(nombres, esperado[1],
                             "idiomas/%s.py y idiomas/%s.py no declaran lo mismo" % (idioma, esperado[0]))

    def test_dias_y_meses_completos(self):
        for idioma in IDIOMAS:
            m = importlib.import_module("idiomas.%s" % idioma)
            self.assertEqual(len(m.DIAS), 7, idioma)
            self.assertEqual(len(m.MESES), 12, idioma)
            self.assertEqual(len(m.MESES_SOLO), 12, idioma)
            self.assertTrue(all(m.DIAS), idioma)
            self.assertTrue(all(m.MESES) and all(m.MESES_SOLO), idioma)


class NotionEnCadaIdioma(unittest.TestCase):
    """Notion tambien habla el idioma de su dueño: los nombres de las bases, los de las
    columnas y los valores que son llaves del sistema."""

    def esquema_es(self):
        """Los nombres tal como los escribe el codigo, sin traducir."""
        import categorias as C
        import notion
        todas = sorted({c for t in C.TIPOS for c in C.nombres(t)})
        return notion._esquemas_es(todas)

    def test_cada_idioma_nombra_todas_las_bases_y_columnas(self):
        import notion
        from config import SIMBOLOS
        sufijos = set(SIMBOLOS) | set(SIMBOLOS.values())
        esquema = self.esquema_es()
        nombres = set(esquema)                                  # las bases
        for props in esquema.values():
            for col in props:
                base, _, suf = col.rpartition(" ")
                nombres.add(base if base and suf in sufijos else col)
        for idioma in IDIOMAS:
            if idioma == ORIGEN:
                continue
            mapa = importlib.import_module("idiomas.%s" % idioma).NOTION_PROP
            faltan = sorted(n for n in nombres if n not in mapa)
            self.assertEqual(faltan, [], "\nidiomas/%s.py no nombra en Notion:\n%s"
                             % (idioma, "\n".join("  " + n for n in faltan)))

    def test_cada_idioma_traduce_las_llaves(self):
        import notion
        valores = set()
        for props in self.esquema_es().values():
            for col, tipo in props.items():
                if col in notion.COLUMNAS_LLAVE and isinstance(tipo.get("select"), dict):
                    valores |= {o["name"] for o in tipo["select"]["options"]}
        valores.discard("—")
        for idioma in IDIOMAS:
            if idioma == ORIGEN:
                continue
            mapa = importlib.import_module("idiomas.%s" % idioma).NOTION_VALOR
            faltan = sorted(v for v in valores if v not in mapa)
            self.assertEqual(faltan, [], "\nidiomas/%s.py no traduce las llaves:\n%s"
                             % (idioma, "\n".join("  " + v for v in faltan)))

    def test_la_vuelta_no_es_ambigua(self):
        """Dos nombres distintos no pueden traducirse igual: al leer de Notion no se sabria
        cual era, y una columna terminaria leyendose como otra."""
        for idioma in IDIOMAS:
            m = importlib.import_module("idiomas.%s" % idioma)
            for cual, mapa in (("NOTION_PROP", m.NOTION_PROP), ("NOTION_VALOR", m.NOTION_VALOR)):
                repetidos = {}
                for es, otro in mapa.items():
                    repetidos.setdefault(otro, []).append(es)
                choques = {k: v for k, v in repetidos.items() if len(v) > 1}
                self.assertEqual(choques, {}, "idiomas/%s.py: %s traduce igual %s"
                                 % (idioma, cual, choques))

    def test_ida_y_vuelta_de_una_fila(self):
        """Lo que se escribe en Notion se tiene que poder volver a leer igual."""
        import notion
        props = {"Tipo": notion.p_select("Gasto"), "Cuenta": notion.p_select("Gastos"),
                 "Categoría": notion.p_select("Cualquiera"), "Monto": notion.p_number(45)}
        enviado = notion._props_a_notion(props)
        pagina = {"properties": {k: dict(v, type=list(v)[0]) for k, v in enviado.items()}}
        leido = notion.fila(pagina)
        self.assertEqual(leido["Tipo"], "Gasto")
        self.assertEqual(leido["Cuenta"], "Gastos")
        self.assertEqual(leido["Categoría"], "Cualquiera")   # del perfil: no se toca
        self.assertEqual(leido["Monto"], 45)

    def test_el_simbolo_de_la_moneda_no_se_traduce(self):
        import notion
        from config import SUFIJO
        self.assertTrue(notion.n_prop("Monto " + SUFIJO).endswith(" " + SUFIJO))
        self.assertEqual(notion.es_prop(notion.n_prop("Monto " + SUFIJO)), "Monto " + SUFIJO)
        self.assertEqual(notion.es_prop(notion.n_prop("Monto USD")), "Monto USD")


if __name__ == "__main__":
    unittest.main()
