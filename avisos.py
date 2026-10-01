#!/usr/bin/env python3
"""Los avisos de cada mañana por Telegram (lo corre finanzas-avisos.timer):

- los recordatorios que tocan hoy (pagar servicios, cuotas de bancos, retirar de Payoneer o PayPal…),
  con botones para marcarlos hechos, registrar el pago o posponerlos a mañana;
- si el dolar esta en buen momento para cambiar (comparado con su promedio del mes);
- las suscripciones que se renuevan en los proximos 3 dias.

    python3 avisos.py              # manda los de hoy
    python3 avisos.py --mostrar    # solo los muestra, sin mandar
"""
import argparse
import sys

import finanzas as F
import informes as I
from config import TELEGRAM_USUARIOS
from notion import Notion, NotionError, cargar_bases
from telegram import Telegram, TelegramError


def botones_aviso(r: dict) -> list:
    """Los botones de un recordatorio: lo que se puede hacer con un toque."""
    rid = r["id"].replace("-", "")
    if r["tipo"] == "Deuda" and r["deuda"]:
        hacer = ("💸 Pagar%s" % (" " + F.en_moneda(r["monto"], r["moneda"]) if r["monto"] else ""), "rc:d:" + rid)
    elif r["tipo"] == "Pago" and r["monto"] and r["categoria"]:
        hacer = ("✅ Pagado %s" % F.en_moneda(r["monto"], r["moneda"]), "rc:p:" + rid)
    else:
        hacer = ("✅ Hecho", "rc:h:" + rid)
    return [[hacer, ("⏰ Mañana", "rc:m:" + rid)]]


def mensajes(notion, bases: dict) -> list:
    """[(texto, botones)] de lo que hay que avisar hoy."""
    out = [(I.texto_aviso(r), botones_aviso(r)) for r in F.avisos_de_hoy(notion, bases)]
    cambio = F.alerta_cambio()
    if cambio:
        out.append((cambio, None))
    for x in F.renovaciones(notion, bases):
        out.append(("🔁 %s se renueva el %s: %s" % (x["nombre"], "/".join(reversed(x["proximo"][5:10].split("-"))),
                                                    F.en_moneda(x["monto"], x["moneda"])), None))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mostrar", action="store_true")
    a = ap.parse_args(argv)
    bases = cargar_bases()
    try:
        F.tc_automatico()          # refresca el tipo de cambio (y su historial) antes de comparar
        lista = mensajes(Notion(), bases)
    except NotionError as exc:
        print("Notion: %s" % exc)
        return 1
    for texto, _ in lista:
        print(texto)
    if a.mostrar or not lista:
        return 0
    try:
        tg = Telegram()
    except TelegramError as exc:
        print(exc)
        return 1
    fallo = 0
    for chat in sorted(TELEGRAM_USUARIOS):
        for texto, botones in lista:
            try:
                tg.enviar(chat, texto, botones)
            except TelegramError as exc:
                print("  [telegram] %s: %s" % (chat, exc))
                fallo = 1
    return fallo


if __name__ == "__main__":
    sys.exit(main())
