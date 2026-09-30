"""Lo que el sistema sabe hacer con el dinero: guardar movimientos, sumar por
periodo, comparar con el presupuesto, medir el patrimonio y dar consejos.

Toda la aritmetica esta aca y no en Notion, para que el resumen de Telegram y
el que queda en la base Resumenes digan exactamente lo mismo.
"""
import json
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import categorias as C
from config import AJUSTES, DATA, TC_EUR, TC_USD, hoy
from notion import (METAS, MOVIMIENTOS, PATRIMONIO, PRESUPUESTO, p_date, p_number, p_select, p_text, p_title)

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


# ---------------------------------------------------------------- tipo de cambio

def ajustes() -> dict:
    try:
        return json.loads(AJUSTES.read_text())
    except (OSError, ValueError):
        return {}


def tipo_de_cambio(moneda: str) -> float:
    if moneda == "PEN":
        return 1.0
    a = ajustes()
    if moneda == "USD":
        return float(a.get("USD") or TC_USD)
    if moneda == "EUR":
        return float(a.get("EUR") or TC_EUR)
    return 1.0


def fijar_tipo_de_cambio(moneda: str, valor: float) -> None:
    a = ajustes()
    a[moneda] = round(float(valor), 4)
    DATA.mkdir(parents=True, exist_ok=True)
    AJUSTES.write_text(json.dumps(a, indent=2))


def soles(monto: float, moneda: str) -> float:
    return round(monto * tipo_de_cambio(moneda), 2)


def s(n: Optional[float]) -> str:
    """S/ 1,234.50 (o -S/ 20.00)."""
    n = float(n or 0)
    return ("-" if n < 0 else "") + "S/ {:,.2f}".format(abs(n))


def pct(x: Optional[float]) -> str:
    return "—" if x is None else "{:.0f}%".format(x * 100)


# ---------------------------------------------------------------- periodos

@dataclass
class Periodo:
    tipo: str        # Diario, Semanal, Mensual
    desde: date
    hasta: date

    @property
    def titulo(self) -> str:
        if self.tipo == "Diario":
            return "%s %d de %s" % (DIAS[self.desde.weekday()].capitalize(), self.desde.day, MESES[self.desde.month - 1])
        if self.tipo == "Semanal":
            return "Semana del %d/%02d al %d/%02d" % (self.desde.day, self.desde.month, self.hasta.day, self.hasta.month)
        return "%s %d" % (MESES[self.desde.month - 1].capitalize(), self.desde.year)

    @property
    def clave(self) -> str:
        """Nombre unico en la base Resumenes: se reescribe en vez de duplicar."""
        if self.tipo == "Diario":
            return "Día %s" % self.desde.isoformat()
        if self.tipo == "Semanal":
            anio, sem, _ = self.desde.isocalendar()
            return "Semana %d-S%02d" % (anio, sem)
        return "Mes %d-%02d" % (self.desde.year, self.desde.month)

    def anterior(self) -> "Periodo":
        if self.tipo == "Diario":
            return dia(self.desde - timedelta(days=1))
        if self.tipo == "Semanal":
            return semana(self.desde - timedelta(days=7))
        return mes(self.desde - timedelta(days=1))

    @property
    def dias(self) -> int:
        return (self.hasta - self.desde).days + 1


def dia(d: Optional[date] = None) -> Periodo:
    d = d or hoy()
    return Periodo("Diario", d, d)


def semana(d: Optional[date] = None) -> Periodo:
    """De lunes a domingo."""
    d = d or hoy()
    ini = d - timedelta(days=d.weekday())
    return Periodo("Semanal", ini, ini + timedelta(days=6))


def mes(d: Optional[date] = None) -> Periodo:
    d = d or hoy()
    return Periodo("Mensual", d.replace(day=1), d.replace(day=monthrange(d.year, d.month)[1]))


# ---------------------------------------------------------------- movimientos

def propiedades_movimiento(mov, origen: str = "Telegram") -> dict:
    tc = tipo_de_cambio(mov.moneda)
    return {
        "Descripción": p_title(mov.descripcion),
        "Tipo": p_select(mov.tipo),
        "Categoría": p_select(mov.categoria),
        "Grupo": p_select(C.grupo(mov.categoria) if mov.tipo == "Gasto" else "—"),
        "Monto": p_number(mov.monto),
        "Moneda": p_select(mov.moneda),
        "Tipo de cambio": p_number(tc),
        "Monto S/": p_number(mov.monto * tc),
        "Medio de pago": p_select(mov.medio),
        "Fecha": p_date(mov.fecha),
        "Origen": p_select(origen),
    }


def guardar_movimiento(notion, bases: dict, mov, origen: str = "Telegram") -> dict:
    return notion.crear_pagina(bases[MOVIMIENTOS], propiedades_movimiento(mov, origen))


def cambiar_categoria(notion, page_id: str, tipo: str, categoria: str) -> dict:
    return notion.editar_pagina(page_id, {
        "Categoría": p_select(categoria),
        "Grupo": p_select(C.grupo(categoria) if tipo == "Gasto" else "—"),
    })


def movimientos(notion, bases: dict, desde: date, hasta: date) -> list:
    filtro = {"and": [{"property": "Fecha", "date": {"on_or_after": desde.isoformat()}},
                      {"property": "Fecha", "date": {"on_or_before": hasta.isoformat()}}]}
    filas = notion.consultar(bases[MOVIMIENTOS], filtro, [{"property": "Fecha", "direction": "ascending"}], limite=5000)
    out = []
    for f in filas:
        monto_s = f.get("Monto S/")
        if monto_s is None:   # fila escrita a mano en Notion, sin la columna en soles
            monto_s = soles(f.get("Monto") or 0, f.get("Moneda") or "PEN")
        out.append({"id": f["_id"], "url": f.get("_url"), "tipo": f.get("Tipo") or "Gasto",
                    "categoria": f.get("Categoría") or "Otros", "monto_s": float(monto_s or 0),
                    "fecha": (f.get("Fecha") or "")[:10], "descripcion": f.get("Descripción") or "",
                    "medio": f.get("Medio de pago")})
    return out


def ultimos(notion, bases: dict, n: int = 10) -> list:
    return notion.consultar(bases[MOVIMIENTOS], orden=[{"timestamp": "created_time", "direction": "descending"}], limite=n)


# ---------------------------------------------------------------- resumen

@dataclass
class Resumen:
    periodo: Periodo
    ingresos: float = 0.0
    gastos: float = 0.0
    ahorro: float = 0.0
    inversion: float = 0.0
    por_categoria: dict = field(default_factory=dict)       # gastos
    ingresos_por_categoria: dict = field(default_factory=dict)
    necesidades: float = 0.0
    deseos: float = 0.0
    cantidad: int = 0
    hormiga: float = 0.0        # gastos chicos (menos de S/ 20) sumados
    hormiga_n: int = 0

    @property
    def balance(self) -> float:
        """Lo que quedo: ingresos menos gastos. Ahorro e inversion salen de aca, no son gasto."""
        return round(self.ingresos - self.gastos, 2)

    @property
    def tasa_ahorro(self) -> Optional[float]:
        if self.ingresos <= 0:
            return None
        return self.balance / self.ingresos

    def parte(self, grupo: str) -> Optional[float]:
        if self.gastos <= 0:
            return None
        return (self.necesidades if grupo == "Necesidad" else self.deseos) / self.gastos

    def top(self, n: int = 5) -> list:
        return sorted(self.por_categoria.items(), key=lambda kv: -kv[1])[:n]


HORMIGA = 20.0


def resumir(movs: list, periodo: Periodo) -> Resumen:
    r = Resumen(periodo)
    for m in movs:
        v = m["monto_s"]
        r.cantidad += 1
        if m["tipo"] == "Ingreso":
            r.ingresos += v
            r.ingresos_por_categoria[m["categoria"]] = r.ingresos_por_categoria.get(m["categoria"], 0) + v
        elif m["tipo"] == "Ahorro":
            r.ahorro += v
        elif m["tipo"] == "Inversión":
            r.inversion += v
        else:
            r.gastos += v
            r.por_categoria[m["categoria"]] = r.por_categoria.get(m["categoria"], 0) + v
            if C.grupo(m["categoria"]) == "Necesidad":
                r.necesidades += v
            else:
                r.deseos += v
            if v < HORMIGA:
                r.hormiga += v
                r.hormiga_n += 1
    for k in ("ingresos", "gastos", "ahorro", "inversion", "necesidades", "deseos", "hormiga"):
        setattr(r, k, round(getattr(r, k), 2))
    return r


# ---------------------------------------------------------------- presupuesto

def presupuesto(notion, bases: dict) -> dict:
    """{categoria: monto mensual en soles}"""
    if PRESUPUESTO not in bases:
        return {}
    out = {}
    for f in notion.consultar(bases[PRESUPUESTO], limite=200):
        if f.get("Categoría") and f.get("Mensual S/"):
            out[f["Categoría"]] = float(f["Mensual S/"])
    return out


def fijar_presupuesto(notion, bases: dict, categoria: str, monto: float) -> dict:
    existentes = notion.consultar(bases[PRESUPUESTO], {"property": "Categoría", "title": {"equals": categoria}}, limite=5)
    props = {"Categoría": p_title(categoria), "Mensual S/": p_number(monto), "Grupo": p_select(C.grupo(categoria))}
    if existentes:
        return notion.editar_pagina(existentes[0]["_id"], props)
    return notion.crear_pagina(bases[PRESUPUESTO], props)


def estado_presupuesto(gastado: dict, plan: dict, avance_mes: float) -> list:
    """[(categoria, gastado, presupuesto, usado)] ordenado de lo mas pasado a lo menos.
    avance_mes: fraccion del mes que ya paso, para decir si vas adelantado."""
    out = []
    for cat, tope in plan.items():
        g = gastado.get(cat, 0.0)
        out.append((cat, g, tope, g / tope if tope else 0))
    for cat, g in gastado.items():   # gastos sin presupuesto
        if cat not in plan:
            out.append((cat, g, 0.0, None))
    return sorted(out, key=lambda x: (x[3] is None, -(x[3] or 0), -x[1]))


# ---------------------------------------------------------------- patrimonio

def patrimonio(notion, bases: dict) -> list:
    if PATRIMONIO not in bases:
        return []
    out = []
    for f in notion.consultar(bases[PATRIMONIO], limite=300):
        valor_s = f.get("Valor S/")
        if valor_s is None:
            valor_s = soles(f.get("Valor") or 0, f.get("Moneda") or "PEN")
        out.append({"id": f["_id"], "nombre": f.get("Nombre") or "?", "clase": f.get("Clase") or "Activo",
                    "tipo": f.get("Tipo") or "", "valor": f.get("Valor") or 0, "moneda": f.get("Moneda") or "PEN",
                    "valor_s": float(valor_s or 0), "actualizado": f.get("Actualizado")})
    return out


def neto(items: list) -> tuple:
    """(activos, pasivos, patrimonio neto, liquidez)"""
    act = sum(i["valor_s"] for i in items if i["clase"] == "Activo")
    pas = sum(i["valor_s"] for i in items if i["clase"] == "Pasivo")
    liq = sum(i["valor_s"] for i in items if i["clase"] == "Activo" and i["tipo"] in C.LIQUIDOS)
    return round(act, 2), round(pas, 2), round(act - pas, 2), round(liq, 2)


def fijar_patrimonio(notion, bases: dict, nombre: str, clase: str, tipo: str, valor: float, moneda: str = "PEN") -> tuple:
    """Crea o actualiza una cuenta, bien o deuda por nombre. Devuelve (pagina, valor anterior en soles o None)."""
    existentes = notion.consultar(bases[PATRIMONIO], {"property": "Nombre", "title": {"equals": nombre}}, limite=5)
    props = {"Nombre": p_title(nombre), "Clase": p_select(clase), "Tipo": p_select(tipo), "Valor": p_number(valor),
             "Moneda": p_select(moneda), "Valor S/": p_number(soles(valor, moneda)), "Actualizado": p_date(hoy())}
    if existentes:
        antes = existentes[0].get("Valor S/")
        return notion.editar_pagina(existentes[0]["_id"], props), antes
    return notion.crear_pagina(bases[PATRIMONIO], props), None


# ---------------------------------------------------------------- metas

def metas(notion, bases: dict) -> list:
    if METAS not in bases:
        return []
    out = []
    for f in notion.consultar(bases[METAS], limite=100):
        obj = float(f.get("Objetivo S/") or 0)
        ah = float(f.get("Ahorrado S/") or 0)
        out.append({"id": f["_id"], "meta": f.get("Meta") or "?", "objetivo": obj, "ahorrado": ah,
                    "avance": (ah / obj) if obj else 0, "prioridad": f.get("Prioridad"), "limite": f.get("Fecha límite")})
    return sorted(out, key=lambda m: (m["prioridad"] != "Muy importante", m["prioridad"] != "Importante", m["meta"]))


def buscar_meta(lista: list, texto: str) -> Optional[dict]:
    t = C.normal(texto).strip()
    if not t:
        return None
    for m in lista:
        if C.normal(m["meta"]) == t:
            return m
    for m in lista:
        if t in C.normal(m["meta"]) or C.normal(m["meta"]) in t:
            return m
    return None


def fijar_meta(notion, bases: dict, nombre: str, objetivo: float, prioridad: Optional[str] = None) -> dict:
    existente = buscar_meta(metas(notion, bases), nombre)
    props = {"Meta": p_title(existente["meta"] if existente else nombre), "Objetivo S/": p_number(objetivo)}
    if prioridad:
        props["Prioridad"] = p_select(prioridad)
    if existente:
        return notion.editar_pagina(existente["id"], props)
    props["Ahorrado S/"] = p_number(0)
    return notion.crear_pagina(bases[METAS], props)


def sumar_a_meta(notion, meta: dict, monto_s: float) -> float:
    nuevo = round(meta["ahorrado"] + monto_s, 2)
    notion.editar_pagina(meta["id"], {"Ahorrado S/": p_number(nuevo)})
    return nuevo


# ---------------------------------------------------------------- consejos

def consejos(r: Resumen, plan: dict = None, items: list = None, gasto_mensual: float = 0.0,
             avance_mes: float = 1.0) -> list:
    """Observaciones concretas sobre los numeros, de la mas urgente a la menos.
    gasto_mensual: gasto promedio de un mes, para medir el fondo de emergencia."""
    plan = plan or {}
    items = items or []
    out = []

    if r.ingresos > 0:
        t = r.tasa_ahorro
        if t < 0:
            out.append("🔴 Gastaste %s más de lo que entró. Revisa las categorías de deseos primero." % s(-r.balance))
        elif t < 0.10:
            out.append("🟠 Te queda el %s de lo que ganas. La meta sana es 20%%: págate primero, separa el ahorro el día que cobras." % pct(t))
        elif t < 0.20:
            out.append("🟡 Ahorras el %s. Vas bien; subir a 20%% es el siguiente paso." % pct(t))
        else:
            out.append("🟢 Ahorras el %s de tus ingresos. Excelente." % pct(t))

    # 50/30/20: necesidades hasta 50% del ingreso, deseos hasta 30%
    if r.ingresos > 0 and r.gastos > 0:
        pn, pd = r.necesidades / r.ingresos, r.deseos / r.ingresos
        if pd > 0.30:
            out.append("🟠 Los deseos se llevan el %s de tus ingresos (regla 50/30/20: hasta 30%%)." % pct(pd))
        if pn > 0.50:
            out.append("🟠 Las necesidades pasan del 50%% de tus ingresos (%s). Mira vivienda, servicios y transporte." % pct(pn))

    # presupuesto
    pasados = []
    for cat, g, tope, usado in estado_presupuesto(r.por_categoria, plan, avance_mes):
        if usado is None or tope <= 0:
            continue
        if usado >= 1:
            pasados.append("%s (%s de %s)" % (cat, s(g), s(tope)))
        elif usado >= 0.8 and usado > avance_mes + 0.1:
            out.append("🟡 %s ya va en %s del presupuesto y el mes va en %s." % (cat, pct(usado), pct(avance_mes)))
    if pasados:
        out.insert(0, "🔴 Pasaste el presupuesto en: " + "; ".join(pasados) + ".")
    if not plan and r.gastos > 0:
        out.append("💡 Aún no tienes presupuesto. Empieza con tus 3 categorías más grandes: /presupuesto comida 800")

    # gastos hormiga
    if r.gastos > 0 and r.hormiga_n >= 5 and r.hormiga / r.gastos > 0.10:
        out.append("🐜 %d gastos chicos suman %s (%s del total). Son los más fáciles de recortar." % (r.hormiga_n, s(r.hormiga), pct(r.hormiga / r.gastos)))

    # fondo de emergencia y deudas
    if items:
        act, pas, net, liq = neto(items)
        if gasto_mensual > 0:
            meses = liq / gasto_mensual
            if meses < 3:
                out.append("🛟 Tu dinero disponible cubre %.1f meses de gastos. Lo recomendable es 3 a 6 meses antes de invertir." % meses)
            elif meses > 12:
                out.append("📈 Tienes %.0f meses de gastos en efectivo o bancos. Lo que pase de 6 meses podría estar invirtiendo." % meses)
        tarjetas = sum(i["valor_s"] for i in items if i["tipo"] == "Tarjeta de crédito")
        if tarjetas > 0:
            out.append("💳 Debes %s en tarjetas. Pagar el total cada mes evita intereses de 40%% a 90%% al año; es la mejor \"inversión\" que tienes." % s(tarjetas))
        if act > 0 and pas / act > 0.5:
            out.append("⚠️ Tus deudas son el %s de lo que tienes. Prioriza bajarlas antes de nuevas compras grandes." % pct(pas / act))
    return out
