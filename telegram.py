"""Cliente minimo de la API de bots de Telegram, con sondeo largo y un candado
para que nunca haya dos procesos leyendo getUpdates con el mismo token.

Los errores nunca llevan la URL: la URL contiene el token y terminaria en el log.
"""
import json
import time
from contextlib import contextmanager
from html import escape
from typing import Optional

import requests

from config import CANDADO, DATA, OFFSET, TELEGRAM_TOKEN

MAX_TEXTO = 4000   # Telegram corta en 4096


class TelegramError(RuntimeError):
    def __init__(self, msg, code=None):
        super().__init__(msg)
        self.code = code


def esc(texto) -> str:
    """Lo que escribe el usuario va escapado: el bot manda HTML."""
    return escape(str(texto if texto is not None else ""), quote=False)


def teclado(botones: Optional[list]) -> Optional[dict]:
    """botones = [[(texto, data), ...], ...] -> reply_markup de Telegram."""
    if not botones:
        return None
    filas = []
    for fila in botones:
        if fila:
            filas.append([({"text": t, "url": d} if d.startswith("http") else {"text": t, "callback_data": d[:64]}) for t, d in fila])
    return {"inline_keyboard": filas} if filas else None


def partir(texto: str, largo: int = MAX_TEXTO) -> list:
    """Corta un texto largo en pedazos por salto de linea, sin pasar el limite."""
    if len(texto) <= largo:
        return [texto]
    partes, actual = [], ""
    for linea in texto.split("\n"):
        if len(linea) > largo:
            if actual:
                partes.append(actual)
                actual = ""
            while len(linea) > largo:
                partes.append(linea[:largo])
                linea = linea[largo:]
        sep = 1 if actual else 0
        if len(actual) + sep + len(linea) > largo:
            if actual:
                partes.append(actual)
            actual = linea
        else:
            actual = linea if not actual else actual + "\n" + linea
    if actual:
        partes.append(actual)
    return [p for p in partes if p]


class Telegram:
    def __init__(self, token: str = TELEGRAM_TOKEN, session=None):
        if not token:
            raise TelegramError("Falta TELEGRAM_TOKEN en el .env")
        self.base = "https://api.telegram.org/bot%s/" % token
        self.s = session or requests.Session()

    def _req(self, metodo: str, **params) -> dict:
        try:
            r = self.s.post(self.base + metodo, json=params, timeout=40)
        except requests.RequestException as exc:
            # sin str(exc): traeria la URL con el token
            raise TelegramError("%s: red: %s" % (metodo, type(exc).__name__))
        try:
            data = r.json()
        except ValueError:
            raise TelegramError("%s: respuesta no es JSON (%s)" % (metodo, r.status_code), r.status_code)
        if not data.get("ok"):
            raise TelegramError("%s: %s" % (metodo, str(data.get("description", ""))[:200]), data.get("error_code"))
        return data.get("result")

    def updates(self, offset: int, timeout: int = 30) -> list:
        return self._req("getUpdates", offset=offset, timeout=timeout,
                         allowed_updates=["message", "callback_query"]) or []

    def enviar(self, chat_id: int, texto: str, botones: Optional[list] = None) -> dict:
        """Manda el texto; si es muy largo lo parte y los botones van en el ultimo pedazo."""
        rm = teclado(botones)
        partes = partir(texto)
        res = None
        for k, parte in enumerate(partes):
            params = {"chat_id": chat_id, "text": parte, "parse_mode": "HTML", "disable_web_page_preview": True}
            if rm and k == len(partes) - 1:
                params["reply_markup"] = rm
            res = self._req("sendMessage", **params)
        return res or {}

    def quitar_botones(self, chat_id: int, message_id: int) -> None:
        """Apaga los botones de un mensaje que ya no espera respuesta."""
        try:
            self._req("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id,
                      reply_markup={"inline_keyboard": []})
        except TelegramError:
            pass

    def responder_callback(self, callback_id: str, texto: str = "") -> None:
        try:
            self._req("answerCallbackQuery", callback_query_id=callback_id, text=texto[:200])
        except TelegramError:
            pass

    def yo(self) -> dict:
        return self._req("getMe")


# ---------------------------------------------------------------- offset

def leer_offset() -> int:
    try:
        return int(json.loads(OFFSET.read_text()).get("offset", 0))
    except (OSError, ValueError, AttributeError):
        return 0


def guardar_offset(offset: int) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    OFFSET.write_text(json.dumps({"offset": offset}))


# ---------------------------------------------------------------- candado

@contextmanager
def turno_del_bot(espera: int = 0):
    """Un solo proceso puede leer la cola en esta maquina. Si hay otro, avisa y no pisa.
    En Windows no hay flock: se sigue sin candado, con aviso."""
    try:
        import fcntl
    except ImportError:
        print("  [aviso] este sistema no tiene candado de archivo: corre una sola copia del bot")
        yield
        return
    CANDADO.parent.mkdir(parents=True, exist_ok=True)
    fh = open(CANDADO, "w")
    limite = time.time() + espera
    while True:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            if time.time() >= limite:
                fh.close()
                raise TelegramError("otro proceso ya esta corriendo el bot")
            time.sleep(3)
    try:
        yield
    finally:
        try:
            fcntl.flock(fh, fcntl.LOCK_UN)
        finally:
            fh.close()
