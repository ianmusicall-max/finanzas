#!/usr/bin/env python3
"""Crea las cinco bases de finanzas (Movimientos, Presupuesto, Patrimonio, Metas y
Resumenes) debajo de la pagina "Finanzas" de Notion. Se puede correr varias veces.

Antes: en Notion abre la pagina "Finanzas", menu ... , Conexiones, y conecta la
misma integracion que usa Core Forever. Copia el ID de la pagina (los 32
caracteres del final de la URL) en NOTION_PARENT_PAGE_ID del .env.
"""
import sys

from config import NOTION_PARENT_PAGE_ID
from notion import Notion, NotionError, crear_bases


def elegir_padre(n: Notion) -> str:
    """Si el .env no trae la pagina padre, busca una llamada "Finanzas" entre las
    que ve la integracion; si no la encuentra, las lista para que elijas."""
    if NOTION_PARENT_PAGE_ID:
        return NOTION_PARENT_PAGE_ID
    paginas = [p for p in n.paginas_accesibles() if p["padre"] in ("workspace", "page_id")]
    finanzas = [p for p in paginas if "finanzas" in (p["titulo"] or "").lower()]
    if len(finanzas) == 1:
        print("Pagina padre: %s (%s)" % (finanzas[0]["titulo"], finanzas[0]["id"]))
        return finanzas[0]["id"]
    print("No sé en qué página crear las bases. Pon una en NOTION_PARENT_PAGE_ID del .env:")
    for p in (finanzas or paginas)[:30]:
        print("  %s  %s" % (p["id"], p["titulo"] or "(sin titulo)"))
    return ""


def main() -> int:
    try:
        n = Notion()
        padre = elegir_padre(n)
        if not padre:
            return 1
        print("Bases en Notion...")
        ids = crear_bases(n, padre)
    except NotionError as exc:
        print("Error: %s" % exc)
        print("Revisa NOTION_TOKEN y NOTION_PARENT_PAGE_ID en el .env, y que la pagina este conectada a la integracion.")
        return 1
    print("\nListo. IDs guardados en data/bases.json:")
    for k, v in ids.items():
        print("  %-12s %s" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
