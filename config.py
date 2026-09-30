"""Configuracion del sistema de finanzas. Todo sale del .env; nada de tokens en el codigo."""
import os
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

# Moneda base: todo se suma en soles. Lo que entra en dolares o euros se
# convierte con este tipo de cambio (se cambia con /tc en el bot).
TC_USD = _num(os.environ.get("TC_USD", ""), 3.75)
TC_EUR = _num(os.environ.get("TC_EUR", ""), 4.10)

# Hora de Lima sin depender de tzdata: Peru no tiene horario de verano.
LIMA = timezone(timedelta(hours=-5), "America/Lima")


def ahora() -> datetime:
    return datetime.now(LIMA)


def hoy():
    return ahora().date()


DATA = ROOT / "data"
BASES = DATA / "bases.json"          # IDs de las bases de Notion que creo setup_notion.py
AJUSTES = DATA / "ajustes.json"      # tipo de cambio que se fijo desde el bot
IMPORTADOS = DATA / "importados.json"  # filas de la hoja ya subidas (para no duplicar)
OFFSET = DATA / "offset.json"        # hasta que update_id ya lei
CANDADO = DATA / "bot.lock"          # un solo proceso leyendo getUpdates
