"""Textos de la interfaz, uno por idioma. Se elige con IDIOMA en el .env.

El perfil dice QUE opciones ve cada persona (`MENU_OPCIONES`); el idioma dice COMO se llaman.
Asi dos personas pueden compartir el mismo menu en distintos idiomas, o el mismo idioma con
menus distintos.

Las frases se traducen BUSCANDO EL ESPANOL, no con una clave inventada:

    t("¿Qué fecha?")   ->  "Какая дата?"

Es a proposito. Con claves (`t("pregunta_fecha")`) el codigo deja de decir lo que sale en
pantalla y hay que ir y volver al diccionario para leerlo; y si alguien se equivoca en la clave,
el bot muestra la clave cruda. Asi el codigo se sigue leyendo solo, y **una frase sin traducir
sale en espanol en vez de romper el bot**: se puede traducir de a poco.

El que avisa de lo que falta es `tests.test_idiomas`, que lee todos los `t("...")` del repo y
comprueba que cada uno este en cada idioma.
"""

import importlib

from config import IDIOMA

_idioma = importlib.import_module("idiomas.%s" % IDIOMA)

BOTONES = _idioma.BOTONES
TEXTOS = getattr(_idioma, "TEXTOS", {})
DIAS = _idioma.DIAS
MESES = _idioma.MESES              # el que acompana a un numero: "31 de octubre" / "31 октября"
MESES_SOLO = _idioma.MESES_SOLO    # el que va suelto: "Octubre" / "октябрь" (en ruso cambia)
EFECTIVO = _idioma.EFECTIVO
MONEDA_NOMBRE = _idioma.MONEDA_NOMBRE
NOTION_PROP = _idioma.NOTION_PROP      # como se llaman las bases y columnas en Notion
NOTION_VALOR = _idioma.NOTION_VALOR    # los valores que son llaves del sistema
COMANDOS = _idioma.COMANDOS            # como se escribe cada comando en este idioma


def t(frase: str) -> str:
    """La frase en el idioma del .env. Si no esta traducida, devuelve el espanol."""
    return TEXTOS.get(frase, frase)
