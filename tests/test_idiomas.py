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


if __name__ == "__main__":
    unittest.main()
