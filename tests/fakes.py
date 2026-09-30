"""Dobles de Notion y Telegram para probar sin red. Guardan las paginas como las
guardaria Notion y las devuelven con fila(), igual que el cliente real."""
import itertools

from notion import leer

BASES = {"Movimientos": "db-mov", "Presupuesto": "db-pre", "Patrimonio": "db-pat", "Metas": "db-met", "Resúmenes": "db-res"}


def _plano(props: dict) -> dict:
    """Propiedades de escritura -> valores planos (lo que devolveria fila())."""
    out = {}
    for k, v in props.items():
        if "title" in v:
            out[k] = "".join(x["text"]["content"] for x in v["title"])
        elif "rich_text" in v:
            out[k] = "".join(x["text"]["content"] for x in v["rich_text"])
        elif "number" in v:
            out[k] = v["number"]
        elif "select" in v:
            out[k] = (v["select"] or {}).get("name")
        elif "date" in v:
            out[k] = (v["date"] or {}).get("start")
    return out


def _cumple(f: dict, filtro) -> bool:
    if not filtro:
        return True
    if "and" in filtro:
        return all(_cumple(f, x) for x in filtro["and"])
    prop, val = filtro["property"], f.get(filtro["property"])
    if "title" in filtro:
        return (val or "") == filtro["title"]["equals"]
    if "date" in filtro:
        d = (val or "")[:10]
        c = filtro["date"]
        if "on_or_after" in c and not (d and d >= c["on_or_after"]):
            return False
        if "on_or_before" in c and not (d and d <= c["on_or_before"]):
            return False
        return True
    return True


class FakeNotion:
    def __init__(self):
        self.dbs = {v: [] for v in BASES.values()}
        self._ids = itertools.count(1)
        self.archivadas = []

    def crear_pagina(self, db_id, propiedades):
        pid = "%032d" % next(self._ids)
        f = _plano(propiedades)
        f.update({"_id": pid, "_url": "https://notion.so/" + pid, "_orden": len(self.dbs[db_id])})
        self.dbs[db_id].append(f)
        return {"id": pid, "url": f["_url"]}

    def _buscar(self, page_id):
        for filas in self.dbs.values():
            for f in filas:
                if f["_id"] == page_id.replace("-", ""):
                    return f
        raise KeyError(page_id)

    def editar_pagina(self, page_id, propiedades):
        self._buscar(page_id).update(_plano(propiedades))
        return {"id": page_id}

    def archivar(self, page_id):
        f = self._buscar(page_id)
        for filas in self.dbs.values():
            if f in filas:
                filas.remove(f)
        self.archivadas.append(page_id)
        return {"id": page_id}

    def consultar(self, db_id, filtro=None, orden=None, limite=1000):
        filas = [dict(f) for f in self.dbs.get(db_id, []) if _cumple(f, filtro)]
        if orden and orden[0].get("timestamp") == "created_time":
            filas.sort(key=lambda f: -f["_orden"])
        elif orden:
            filas.sort(key=lambda f: f.get(orden[0]["property"]) or "")
        return filas[:limite]


class FakeTelegram:
    def __init__(self):
        self.enviados = []
        self.apagados = []

    def enviar(self, chat, texto, botones=None):
        self.enviados.append((chat, texto, botones))
        return {"message_id": len(self.enviados)}

    def quitar_botones(self, chat, message_id):
        self.apagados.append((chat, message_id))

    def responder_callback(self, cid, texto=""):
        pass

    def updates(self, offset, timeout=30):
        return []

    def yo(self):
        return {"username": "finanzas_test_bot"}

    @property
    def ultimo(self):
        return self.enviados[-1][1] if self.enviados else ""

    def botones(self):
        b = self.enviados[-1][2] or []
        return [x for fila in b for x in fila]

    def data_de(self, etiqueta):
        for t, d in self.botones():
            if etiqueta.lower() in t.lower():
                return d
        raise AssertionError("no hay boton %r en %r" % (etiqueta, [t for t, _ in self.botones()]))
