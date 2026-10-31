"""Configuracion del sistema de finanzas. Todo sale del .env; nada de tokens en el codigo."""
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "").strip()
NOTION_PARENT_PAGE_ID = os.environ.get("NOTION_PARENT_PAGE_ID", "").strip().replace("-", "")


def _ids(texto: str) -> set:
    return {int(x) for x in texto.replace(";", ",").split(",") if x.strip().isdigit()}


def _num(texto: str, defecto: float) -> float:
    try:
        return float(str(texto).replace(",", "."))
    except (TypeError, ValueError):
        return defecto


# Quien puede usar el bot. Si esta vacio, el bot no le hace caso a nadie y
# le dice su ID a quien escriba, para que lo pegues aca. A estos mismos IDs
# les llegan los resumenes diarios y semanales.
TELEGRAM_USUARIOS = _ids(os.environ.get("TELEGRAM_USUARIOS", ""))

# La moneda en la que se suma todo. Las columnas de Notion llevan su simbolo en el nombre
# ("Monto S/", "Monto ₽"), asi que cambiarla crea columnas distintas: se define una vez, antes de
# correr setup_notion.py, y no se toca mas. PEN es la de siempre, para no mover nada de lo que ya hay.
MONEDA_BASE = (os.environ.get("MONEDA_BASE", "PEN").strip().upper() or "PEN")
SIMBOLOS = {"PEN": "S/", "USD": "$", "RUB": "₽", "EUR": "€"}
SUFIJO = SIMBOLOS.get(MONEDA_BASE, MONEDA_BASE)
# El rublo no se escribe con centimos: ₽ 1,500, no ₽ 1,500.00.
DECIMALES = {"RUB": 0}


def columna(nombre: str) -> str:
    """El nombre de una columna de Notion en la moneda base: columna("Monto") -> "Monto S/"."""
    return "%s %s" % (nombre, SUFIJO)


# Cuantas unidades de cada moneda vale 1 dolar. De aca sale el tipo de cambio contra la
# MONEDA_BASE que sea, y el respaldo para cuando no hay internet.
#
# Antes esto eran tres numeros sueltos (TC_USD=3.75 ...) que querian decir "soles por unidad":
# el sistema entero estaba atado al sol. Con la base en rublos ese 3.75 habria convertido mal
# cada monto en dolares, en silencio.
# Los numeros estan elegidos para que con base PEN salgan exactamente los de siempre
# (3.75 soles por dolar, 4.10 por euro, 0.045 por rublo): nada cambia para quien ya lo usa.
POR_USD = {"USD": 1.0, "PEN": 3.75, "EUR": 0.914634, "RUB": 83.3333}


def tc_defecto(moneda: str) -> float:
    """Unidades de la MONEDA_BASE por 1 unidad de `moneda`, sin salir a internet."""
    if moneda == MONEDA_BASE:
        return 1.0
    return POR_USD.get(MONEDA_BASE, 1.0) / POR_USD.get(moneda, 1.0)


# Respaldo por si no hay conexion. Se puede fijar a mano en el .env con TC_USD, TC_EUR...,
# siempre en unidades de la MONEDA_BASE (con base PEN, TC_USD son soles por dolar; con base
# RUB, rublos por dolar). Normalmente no hace falta ponerlos: los de arriba ya sirven.
TC_DEFECTO = {m: _num(os.environ.get("TC_%s" % m, ""), tc_defecto(m))
              for m in POR_USD if m != MONEDA_BASE}
# Si es 1 (lo normal), el tipo de cambio del dia se baja solo de internet; los de arriba
# quedan de respaldo por si no hay conexion. Con /tc 3.38 se fija uno a mano.
TC_AUTO = os.environ.get("TC_AUTO", "1").strip() not in ("0", "no", "false", "")

# Zona horaria del dueño, sin depender de tzdata: ni Lima ni Moscu tienen horario de verano, asi
# que alcanza con el desfase fijo. Para otra zona se puede escribir "UTC+2" o "-3" directo.
# Los timers de systemd leen ZONA_HORARIA del .env (deploy/poner-timers.sh).
ZONAS = {"America/Lima": -5, "Europe/Moscow": 3}
ZONA_HORARIA = os.environ.get("ZONA_HORARIA", "America/Lima").strip() or "America/Lima"


def _desfase(zona: str) -> float:
    if zona in ZONAS:
        return ZONAS[zona]
    m = re.match(r"^(?:UTC|GMT)?([+-]?\d{1,2})(?::(\d{2}))?$", zona.replace(" ", ""))
    if not m:
        raise SystemExit("ZONA_HORARIA no se entiende: %r. Pon una de %s, o algo como UTC+3."
                         % (zona, " / ".join(sorted(ZONAS))))
    horas = int(m.group(1))
    minutos = int(m.group(2) or 0)
    return horas + (minutos / 60.0 if horas >= 0 else -minutos / 60.0)


TZ = timezone(timedelta(hours=_desfase(ZONA_HORARIA)), ZONA_HORARIA)


def ahora() -> datetime:
    return datetime.now(TZ)


def hoy():
    return ahora().date()


# El idioma de los botones y los textos del bot (idiomas/<IDIOMA>.py).
IDIOMA = (os.environ.get("IDIOMA", "es").strip().lower() or "es")

# Quien es el dueño de este sistema: elige perfiles/<PERFIL>.py, donde viven sus categorias,
# sus bancos y sus alias. El codigo es el mismo para todos; esto es lo unico que cambia.
PERFIL = os.environ.get("PERFIL", "jose").strip() or "jose"

DATA = ROOT / "data"
BASES = DATA / "bases.json"          # IDs de las bases de Notion que creo setup_notion.py
AJUSTES = DATA / "ajustes.json"      # tipo de cambio que se fijo desde el bot
IMPORTADOS = DATA / "importados.json"  # filas de la hoja ya subidas (para no duplicar)
OFFSET = DATA / "offset.json"        # hasta que update_id ya lei
CANDADO = DATA / "bot.lock"          # un solo proceso leyendo getUpdates
