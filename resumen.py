#!/usr/bin/env python3
"""Calcula el resumen de un periodo, lo guarda en la base Resumenes de Notion y
lo manda por Telegram. Lo corren los temporizadores del servidor:

    python3 resumen.py diario     # a las 21:30: el dia de hoy
    python3 resumen.py semanal    # domingo 20:00: de lunes a domingo
    python3 resumen.py mensual    # dia 1 a las 08:00: el mes que termino

    --fecha 2026-09-15   calcula el periodo que contiene esa fecha
    --sin-telegram       solo Notion (para rellenar periodos pasados)
"""
import argparse
import sys
from datetime import date, timedelta

import finanzas as F
from config import TELEGRAM_USUARIOS
from informes import Informe, url_grafico_semana
from notion import Notion, NotionError, cargar_bases
from telegram import Telegram, TelegramError


def periodo(tipo: str, fecha: date) -> F.Periodo:
    if tipo == "diario":
        return F.dia(fecha)
    if tipo == "semanal":
        return F.semana(fecha)
    return F.mes(fecha)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tipo", choices=["diario", "semanal", "mensual"])
    ap.add_argument("--fecha", help="AAAA-MM-DD; por defecto hoy (o el mes pasado si es mensual)")
    ap.add_argument("--sin-telegram", action="store_true")
    a = ap.parse_args(argv)

    if a.fecha:
        fecha = date.fromisoformat(a.fecha)
    elif a.tipo == "mensual":
        fecha = F.hoy().replace(day=1) - timedelta(days=1)   # corre el dia 1: el mes que acaba de terminar
    else:
        fecha = F.hoy()

    bases = cargar_bases()
    if "Movimientos" not in bases:
        print("Falta data/bases.json. Corre primero: python3 setup_notion.py")
        return 1
    try:
        inf = Informe(Notion(), bases, periodo(a.tipo, fecha))
        inf.guardar()
    except NotionError as exc:
        print("Notion: %s" % exc)
        return 1
    texto = inf.texto()
    print(texto.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", ""))

    if a.sin_telegram:
        return 0
    if not TELEGRAM_USUARIOS:
        print("TELEGRAM_USUARIOS vacio: no mando el resumen por Telegram.")
        return 0
    try:
        tg = Telegram()
    except TelegramError as exc:
        print(exc)
        return 1
    grafico = None
    if a.tipo == "semanal":
        try:
            grafico = url_grafico_semana(inf.notion, bases, fecha)
        except NotionError:
            grafico = None
    fallo = 0
    for chat in sorted(TELEGRAM_USUARIOS):
        try:
            tg.enviar(chat, texto)
            if grafico:
                tg.enviar_foto(chat, grafico, "🖼 Tus gastos de la semana por categoría")
        except TelegramError as exc:
            print("  [telegram] %s: %s" % (chat, exc))
            fallo = 1
    return fallo


if __name__ == "__main__":
    sys.exit(main())
