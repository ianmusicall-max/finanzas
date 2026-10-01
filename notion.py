"""Cliente minimo de la API de Notion y el esquema de las bases de finanzas.

Solo usa `requests`. Las bases se crean una vez con setup_notion.py debajo de la
pagina "Finanzas"; sus IDs quedan en data/bases.json y el bot las usa desde ahi.
"""
import json
import time
from datetime import date
from typing import Optional

import requests

import categorias as C
from config import BASES, DATA, NOTION_PARENT_PAGE_ID, NOTION_TOKEN

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"


class NotionError(RuntimeError):
    def __init__(self, msg, status=None, code=None):
        super().__init__(msg)
        self.status = status
        self.code = code


# ---------------------------------------------------------------- valores

def p_title(texto: str) -> dict:
    return {"title": [{"text": {"content": (texto or "")[:2000]}}]}


def p_text(texto: Optional[str]) -> dict:
    return {"rich_text": [{"text": {"content": texto[:2000]}}] if texto else []}


def p_number(n) -> dict:
    return {"number": None if n is None or n == "" else round(float(n), 2)}


def p_select(nombre: Optional[str]) -> dict:
    return {"select": {"name": nombre} if nombre else None}


def p_date(d, hasta=None) -> dict:
    if not d:
        return {"date": None}
    v = {"start": d.isoformat() if isinstance(d, date) else d}
    if hasta:
        v["end"] = hasta.isoformat() if isinstance(hasta, date) else hasta
    return {"date": v}


def leer(prop: dict):
    """Devuelve el valor plano de una propiedad tal como la manda Notion."""
    t = prop.get("type")
    if t == "title":
        return "".join(x.get("plain_text", "") for x in prop.get("title", []))
    if t == "rich_text":
        return "".join(x.get("plain_text", "") for x in prop.get("rich_text", []))
    if t == "number":
        return prop.get("number")
    if t == "select":
        return (prop.get("select") or {}).get("name")
    if t == "date":
        return (prop.get("date") or {}).get("start")
    if t == "checkbox":
        return prop.get("checkbox")
    if t == "formula":
        f = prop.get("formula") or {}
        return f.get(f.get("type"))
    return None


def fila(page: dict) -> dict:
    """Una pagina de Notion como diccionario {propiedad: valor} mas id y url."""
    out = {k: leer(v) for k, v in (page.get("properties") or {}).items()}
    out["_id"] = page.get("id")
    out["_url"] = page.get("url")
    return out


# ---------------------------------------------------------------- cliente

class Notion:
    def __init__(self, token: str = NOTION_TOKEN, session=None):
        if not token:
            raise NotionError("Falta NOTION_TOKEN en el .env")
        self.s = session or requests.Session()
        self.s.headers.update({
            "Authorization": "Bearer " + token,
            "Notion-Version": VERSION,
            "Content-Type": "application/json",
        })

    def _req(self, metodo: str, ruta: str, cuerpo: Optional[dict] = None) -> dict:
        """Reintenta ante 429 y 5xx. Un corte de red se reintenta solo en lecturas:
        un POST que crea una pagina podria haber llegado y duplicaria."""
        lectura = metodo == "GET" or ruta.endswith("/query") or ruta == "/search"
        for intento in range(3):
            try:
                r = self.s.request(metodo, API + ruta, json=cuerpo, timeout=30)
            except requests.RequestException as exc:
                if lectura and intento < 2:
                    time.sleep(2 * (intento + 1))
                    continue
                raise NotionError("%s %s -> red: %s" % (metodo, ruta, type(exc).__name__))
            if (r.status_code == 429 or (r.status_code >= 500 and lectura)) and intento < 2:
                try:
                    espera = float(r.headers.get("Retry-After", 1))
                except ValueError:
                    espera = 1.0
                time.sleep(min(max(espera, 1.0), 10.0))
                continue
            if r.status_code >= 400:
                try:
                    j = r.json()
                    msg, code = j.get("message", r.text), j.get("code")
                except ValueError:
                    msg, code = r.text, None
                raise NotionError("%s %s -> %s: %s" % (metodo, ruta, r.status_code, str(msg)[:300]), r.status_code, code)
            return r.json()
        raise NotionError("%s %s -> sin respuesta" % (metodo, ruta))

    def crear_base(self, titulo: str, propiedades: dict, parent_page_id: str, icono: str = "") -> dict:
        cuerpo = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": titulo}}],
            "properties": propiedades,
        }
        if icono:
            cuerpo["icon"] = {"type": "emoji", "emoji": icono}
        return self._req("POST", "/databases", cuerpo)

    def base(self, db_id: str) -> dict:
        return self._req("GET", "/databases/" + db_id)

    def crear_pagina(self, db_id: str, propiedades: dict) -> dict:
        return self._req("POST", "/pages", {"parent": {"database_id": db_id}, "properties": propiedades})

    def editar_pagina(self, page_id: str, propiedades: dict) -> dict:
        return self._req("PATCH", "/pages/" + page_id, {"properties": propiedades})

    def archivar(self, page_id: str) -> dict:
        return self._req("PATCH", "/pages/" + page_id, {"archived": True})

    def pagina(self, page_id: str) -> dict:
        return fila(self._req("GET", "/pages/" + page_id))

    def consultar(self, db_id: str, filtro: Optional[dict] = None, orden: Optional[list] = None,
                  limite: int = 1000) -> list:
        """Todas las filas que cumplen el filtro, pagina por pagina (Notion da 100 por vez)."""
        cuerpo = {"page_size": min(limite, 100)}
        if filtro:
            cuerpo["filter"] = filtro
        if orden:
            cuerpo["sorts"] = orden
        out = []
        while True:
            res = self._req("POST", "/databases/%s/query" % db_id, cuerpo)
            out.extend(fila(p) for p in res.get("results", []))
            if not res.get("has_more") or len(out) >= limite:
                return out[:limite]
            cuerpo["start_cursor"] = res.get("next_cursor")

    def paginas_accesibles(self) -> list:
        """Paginas que el usuario conecto a la integracion, para elegir la pagina padre."""
        res = self._req("POST", "/search", {"filter": {"property": "object", "value": "page"}, "page_size": 100})
        out = []
        for o in res.get("results", []):
            props = o.get("properties") or {}
            pr = props.get("title") or next((v for v in props.values() if v.get("type") == "title"), {})
            titulo = "".join(x.get("plain_text", "") for x in pr.get("title", []))
            out.append({"id": o["id"], "titulo": titulo, "padre": (o.get("parent") or {}).get("type")})
        return out


# ---------------------------------------------------------------- esquema

def _sel(opciones: list) -> dict:
    return {"select": {"options": [{"name": o} for o in opciones]}}


def _num(formato: str = "number") -> dict:
    return {"number": {"format": formato}}


MOVIMIENTOS, PRESUPUESTO, PATRIMONIO, METAS, RESUMENES = "Movimientos", "Presupuesto", "Patrimonio", "Metas", "Resúmenes"
DEUDAS = "Deudas"
ICONOS = {MOVIMIENTOS: "💸", PRESUPUESTO: "🧾", PATRIMONIO: "🏦", METAS: "🎯", RESUMENES: "📊", DEUDAS: "💳"}
TIPOS_DEUDA = ["Tarjeta de crédito", "Préstamo", "Hipoteca", "Persona", "Otra"]


def esquemas() -> dict:
    todas = sorted({c for t in C.TIPOS for c in C.nombres(t)})
    return {
        MOVIMIENTOS: {
            "Descripción": {"title": {}},
            "Tipo": _sel(C.TIPOS),
            "Categoría": _sel(todas),
            "Grupo": _sel(C.GRUPOS + ["—"]),
            "Cuenta": _sel(C.CUENTAS),
            "Monto": _num(),
            "Moneda": _sel(C.MONEDAS),
            "Tipo de cambio": _num(),
            "Monto S/": _num(),
            "Medio de pago": _sel(C.MEDIOS),
            "Fecha": {"date": {}},
            "Origen": _sel(["Telegram", "Hoja 2025", "Manual"]),
            "Creado": {"created_time": {}},
        },
        PRESUPUESTO: {
            "Categoría": {"title": {}},
            "Mensual S/": _num(),
            "Grupo": _sel(C.GRUPOS),
            "Notas": {"rich_text": {}},
        },
        PATRIMONIO: {
            "Nombre": {"title": {}},
            "Clase": _sel(["Activo", "Pasivo"]),
            "Tipo": _sel(C.ACTIVOS + C.PASIVOS),
            "Valor": _num(),
            "Moneda": _sel(C.MONEDAS),
            "Valor S/": _num(),
            "Actualizado": {"date": {}},
            "Notas": {"rich_text": {}},
        },
        METAS: {
            "Meta": {"title": {}},
            "Objetivo S/": _num(),
            "Ahorrado S/": _num(),
            "Avance": {"formula": {"expression": 'if(prop("Objetivo S/") > 0, min(prop("Ahorrado S/") / prop("Objetivo S/"), 1), 0)'}},
            "Prioridad": _sel(["Muy importante", "Importante", "Puede esperar"]),
            "Fecha límite": {"date": {}},
        },
        RESUMENES: {
            "Periodo": {"title": {}},
            "Tipo": _sel(["Diario", "Semanal", "Mensual"]),
            "Fechas": {"date": {}},
            "Ingresos S/": _num(),
            "Gastos S/": _num(),
            "Ahorro S/": _num(),
            "Inversión S/": _num(),
            "Balance S/": _num(),
            "Tasa de ahorro": _num("percent"),
            "Necesidades %": _num("percent"),
            "Deseos %": _num("percent"),
            "Patrimonio neto S/": _num(),
            "Principales gastos": {"rich_text": {}},
            "Alertas": {"rich_text": {}},
        },
        DEUDAS: {
            "Deuda": {"title": {}},
            "Tipo": _sel(TIPOS_DEUDA),
            "Acreedor": {"rich_text": {}},
            "Monto original": _num(),
            "Saldo": _num(),
            "Moneda": _sel(C.MONEDAS),
            "Saldo S/": _num(),
            "Tasa anual": _num("percent"),
            "Cuota mensual": _num(),
            "Día de pago": _num(),
            "Inicio": {"date": {}},
            "Estado": _sel(["Activa", "Pagada"]),
            "Actualizado": {"date": {}},
            "Notas": {"rich_text": {}},
        },
    }


def cargar_bases() -> dict:
    try:
        return json.loads(BASES.read_text())
    except (OSError, ValueError):
        return {}


def guardar_bases(ids: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    BASES.write_text(json.dumps(ids, indent=2, ensure_ascii=False))


def _sin_guiones(x: str) -> str:
    return (x or "").replace("-", "").lower()


def buscar_base_bajo(notion: Notion, titulo: str, parent: str) -> Optional[str]:
    """La base con ese titulo exacto debajo de la pagina padre, si ya existe.
    Asi setup_notion.py no duplica bases aunque data/bases.json no este."""
    res = notion._req("POST", "/search", {"query": titulo, "filter": {"property": "object", "value": "database"}, "page_size": 50})
    for o in res.get("results", []):
        t = "".join(x.get("plain_text", "") for x in o.get("title", [])).strip()
        padre = o.get("parent") or {}
        if t.lower() == titulo.lower() and _sin_guiones(padre.get("page_id", "")) == _sin_guiones(parent) and not o.get("archived"):
            return o["id"]
    return None


def crear_bases(notion: Notion, parent: str = NOTION_PARENT_PAGE_ID, log=print) -> dict:
    """Crea las bases debajo de la pagina padre. Se puede correr varias
    veces: lo que ya existe se respeta, y a lo existente se le agregan las
    propiedades nuevas del esquema (nunca se borra una columna)."""
    ids = cargar_bases()
    for nombre, props in esquemas().items():
        if nombre in ids:
            try:
                b = notion.base(ids[nombre])
                if not (b.get("archived") or b.get("in_trash")):
                    faltan = {k: v for k, v in props.items() if k not in (b.get("properties") or {})}
                    if faltan:
                        notion._req("PATCH", "/databases/" + ids[nombre], {"properties": faltan})
                        log("  %-12s ya existe; agregué %s" % (nombre, ", ".join(faltan)))
                    else:
                        log("  %-12s ya existe" % nombre)
                    continue
                log("  %-12s está en la papelera; la creo de nuevo" % nombre)
            except NotionError as exc:
                if exc.status != 404:
                    raise NotionError("no pude verificar %s (%s); no creo nada para no duplicar" % (nombre, exc))
                log("  %-12s estaba anotada pero no se encuentra; la creo de nuevo" % nombre)
        existente = buscar_base_bajo(notion, nombre, parent)
        if existente:
            ids[nombre] = existente
            log("  %-12s encontrada en Notion" % nombre)
        else:
            ids[nombre] = notion.crear_base(nombre, props, parent, ICONOS.get(nombre, ""))["id"]
            log("  %-12s creada" % nombre)
        guardar_bases(ids)
    return ids
