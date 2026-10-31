"""Textos de la interfaz, uno por idioma. Se elige con IDIOMA en el .env.

El perfil dice QUE opciones ve cada persona (`MENU_OPCIONES`); el idioma dice COMO se llaman.
Así dos personas pueden compartir el mismo menú en distintos idiomas, o el mismo idioma con
menús distintos.
"""

import importlib

from config import IDIOMA

_idioma = importlib.import_module("idiomas.%s" % IDIOMA)
BOTONES = _idioma.BOTONES
