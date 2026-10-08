"""Lo que el sistema sabe hacer con el dinero: guardar movimientos, sumar por
periodo, comparar con el presupuesto, medir el patrimonio y dar consejos.

Toda la aritmetica esta aca y no en Notion, para que el resumen de Telegram y
el que queda en la base Resumenes digan exactamente lo mismo.
"""
import json
import time
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import categorias as C
import requests

import config
from config import AJUSTES, DATA, TC_EUR, TC_RUB, TC_USD, ahora, hoy
from notion import (DEUDAS, METAS, MOVIMIENTOS, PATRIMONIO, PRESUPUESTO, RECORDATORIOS, SUSCRIPCIONES, NotionError, p_date, p_number, p_select, p_text, p_title)

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


# ---------------------------------------------------------------- tipo de cambio

def ajustes() -> dict:
    try:
        return json.loads(AJUSTES.read_text())
    except (OSError, ValueError):
        return {}


# Tipo de cambio del dia: dos fuentes gratuitas sin clave, la segunda de respaldo.
# Las dos dan cuanto vale 1 dolar en cada moneda; de ahi sale cuantos soles vale 1 USD, 1 EUR o 1 RUB.
FUENTES_TC = [
    ("https://open.er-api.com/v6/latest/USD", lambda j: j["rates"]),
    ("https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
     lambda j: {k.upper(): v for k, v in j["usd"].items()}),
]
VIGENCIA_TC = 6 * 3600      # se vuelve a bajar cada 6 horas
REINTENTO_TC = 30 * 60      # si no hubo internet, no se reintenta antes de 30 minutos
ESPERA_TC = 5               # por fuente: si cuelga, se corta a los 5 segundos y usa el de respaldo
DEFECTO_TC = {"USD": TC_USD, "EUR": TC_EUR, "RUB": TC_RUB}


def _guardar_ajustes(a: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    AJUSTES.write_text(json.dumps(a, indent=2, ensure_ascii=False))


def _descargar_tc() -> Optional[dict]:
    """{"USD": soles por dolar, "EUR": ..., "RUB": ...} o None si ninguna fuente respondio bien."""
    for url, leer in FUENTES_TC:
        try:
            r = requests.get(url, timeout=ESPERA_TC)
            r.raise_for_status()
            por_usd = leer(r.json())
            pen, eur, rub = float(por_usd["PEN"]), float(por_usd["EUR"]), float(por_usd["RUB"])
            tc = {"USD": round(pen, 4), "EUR": round(pen / eur, 4), "RUB": round(pen / rub, 6)}
        except (requests.RequestException, ValueError, KeyError, TypeError, ZeroDivisionError):
            continue
        if 2 < tc["USD"] < 6 and 2 < tc["EUR"] < 7 and 0.01 < tc["RUB"] < 0.2:   # descarta datos absurdos
            return tc
    return None


def tc_automatico() -> dict:
    """El tipo de cambio del dia guardado en ajustes; lo baja de nuevo si tiene mas de 6 horas."""
    a = ajustes()
    auto = a.get("auto") or {}
    t = time.time()
    if config.TC_AUTO and t - auto.get("ts", 0) > VIGENCIA_TC and t - a.get("intento_tc", 0) > REINTENTO_TC:
        # El intento queda anotado ANTES de salir a internet: si la fuente cuelga y el
        # servicio se reinicia en ese rato (el timer baja cambios cada 5 minutos), al
        # arrancar de nuevo no se vuelve a colgar; espera los 30 minutos como corresponde.
        a["intento_tc"] = t
        try:
            _guardar_ajustes(a)
        except OSError:
            pass
        nuevo = _descargar_tc()
        if nuevo:
            a = ajustes()                                  # por si se fijo uno a mano mientras bajaba
            nuevo.update({"ts": t, "fecha": ahora().strftime("%d/%m %H:%M")})
            a["auto"] = auto = nuevo
            # historial de un valor por dia, para avisar cuando el cambio esta bueno
            h = a.setdefault("historial_tc", {})
            h[hoy().isoformat()] = {m: nuevo[m] for m in ("USD", "EUR", "RUB")}
            for viejo in sorted(h)[:-90]:
                h.pop(viejo, None)
            a["intento_tc"] = t
            try:
                _guardar_ajustes(a)
            except OSError:
                pass
    return auto


def tc_fijo(moneda: str) -> Optional[float]:
    """El que se fijo a mano con /tc, si hay."""
    v = ajustes().get(moneda)
    return float(v) if v else None


def tipo_de_cambio(moneda: str) -> float:
    """Soles por 1 unidad de la moneda: el fijado a mano, si no el del dia, si no el del .env."""
    if moneda not in DEFECTO_TC:
        return 1.0
    return tc_fijo(moneda) or float(tc_automatico().get(moneda) or DEFECTO_TC[moneda])


def fijar_tipo_de_cambio(moneda: str, valor: float) -> None:
    a = ajustes()
    a[moneda] = round(float(valor), 4 if moneda != "RUB" else 6)
    _guardar_ajustes(a)


def tc_a_automatico() -> None:
    """Quita los tipos de cambio fijados a mano y fuerza a bajar el del dia."""
    a = ajustes()
    for m in DEFECTO_TC:
        a.pop(m, None)
    a.pop("intento_tc", None)
    (a.get("auto") or {}).pop("ts", None)
    _guardar_ajustes(a)


def soles(monto: float, moneda: str) -> float:
    return round(monto * tipo_de_cambio(moneda), 2)


def s(n: Optional[float]) -> str:
    """S/ 1,234.50 (o -S/ 20.00)."""
    n = float(n or 0)
    return ("-" if n < 0 else "") + "S/ {:,.2f}".format(abs(n))


def en_dolares(soles_: float) -> float:
    return round(float(soles_ or 0) / tipo_de_cambio("USD"), 2)


def en_rublos(soles_: float) -> float:
    return round(float(soles_ or 0) / tipo_de_cambio("RUB"), 0)


def s3(n: Optional[float]) -> str:
    """El mismo monto en soles, dolares y rublos: S/ 1,000.00 · $ 296.03 · ₽ 23,385"""
    n = float(n or 0)
    signo = "-" if n < 0 else ""
    return "%s · %s$ {:,.2f} · %s₽ {:,.0f}".format(abs(en_dolares(n)), abs(en_rublos(n))) % (s(n), signo, signo)


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


# ---------------------------------------------------------------- limite del dia a dia

SIMBOLO = {"PEN": "S/ ", "USD": "$ ", "RUB": "₽ ", "EUR": "€ "}


def en_moneda(monto: float, moneda: str) -> str:
    """₽ 1,500 · $ 19.00 · S/ 64.00"""
    if moneda == "RUB":
        return "₽ {:,.0f}".format(monto)
    return SIMBOLO.get(moneda, moneda + " ") + "{:,.2f}".format(monto)


def limite() -> Optional[tuple]:
    """(monto por dia, moneda) que se fijo con /limite, o None."""
    l = ajustes().get("limite") or {}
    return (float(l["monto"]), l.get("moneda", "PEN")) if l.get("monto") else None


def fijar_limite(monto: float, moneda: str = "PEN") -> None:
    a = ajustes()
    if monto > 0:
        a["limite"] = {"monto": round(float(monto), 2), "moneda": moneda}
    else:
        a.pop("limite", None)
    _guardar_ajustes(a)


def es_dia_a_dia(m: dict) -> bool:
    return m["tipo"] == "Gasto" and m["categoria"] not in C.CATEGORIAS_FIJAS


def estado_limite(notion, bases: dict, d: Optional[date] = None) -> Optional[dict]:
    """Cuanto va del limite del dia a dia hoy, en la semana y en el mes, en la moneda del limite.
    La semana vale 7 dias de limite y el mes, los dias que tenga."""
    lim = limite()
    if not lim or MOVIMIENTOS not in bases:
        return None
    por_dia, moneda = lim
    d = d or hoy()
    sem, m = semana(d), mes(d)
    desde = min(sem.desde, m.desde)
    movs = [x for x in movimientos(notion, bases, desde, d) if es_dia_a_dia(x)]
    tc = tipo_de_cambio(moneda)
    out = {"moneda": moneda, "por_dia": por_dia}
    for clave, ini, fin in (("dia", d, d), ("semana", sem.desde, sem.hasta), ("mes", m.desde, m.hasta)):
        dias = (fin - ini).days + 1
        tope = round(por_dia * dias, 2)
        gastado = round(sum(x["monto_s"] for x in movs if ini.isoformat() <= x["fecha"] <= d.isoformat()) / tc, 2)
        quedan_dias = (fin - d).days + 1
        queda = round(tope - gastado, 2)
        out[clave] = {"gastado": gastado, "tope": tope, "queda": queda, "usado": gastado / tope if tope else 0,
                      "dias": quedan_dias, "por_dia": round(max(queda, 0) / quedan_dias, 2) if quedan_dias else 0}
    return out


def marca_limite(usado: float) -> str:
    return "🔴" if usado > 1 else "🟡" if usado >= 0.8 else "🟢"


# ---------------------------------------------------------------- movimientos

def propiedades_movimiento(mov, origen: str = "Telegram") -> dict:
    tc = tipo_de_cambio(mov.moneda)
    return {
        "Descripción": p_title(mov.descripcion),
        "Tipo": p_select(mov.tipo),
        "Categoría": p_select(mov.categoria),
        "Grupo": p_select(C.grupo(mov.categoria) if mov.tipo == "Gasto" else "—"),
        "Cuenta": p_select(getattr(mov, "cuenta", None)),
        "Monto": p_number(mov.monto),
        "Moneda": p_select(mov.moneda),
        "Tipo de cambio": p_number(tc),
        "Monto S/": p_number(mov.monto * tc),
        "Monto USD": p_number(en_dolares(mov.monto * tc)),
        "Monto RUB": p_number(en_rublos(mov.monto * tc)),
        "Medio de pago": p_select(mov.medio),
        "Tarjeta": p_select(getattr(mov, "tarjeta", None)),
        "Cuotas": p_number(getattr(mov, "cuotas", None)),
        "Frecuencia": p_select(getattr(mov, "frecuencia", None)),
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
                    "medio": f.get("Medio de pago"), "cuenta": f.get("Cuenta"), "frecuencia": f.get("Frecuencia")})
    return out


def ultimos(notion, bases: dict, n: int = 10) -> list:
    return notion.consultar(bases[MOVIMIENTOS], orden=[{"timestamp": "created_time", "direction": "descending"}], limite=n)


def movimiento(notion, bases: dict, page_id: str) -> Optional[dict]:
    """Un movimiento ya guardado, con lo que hace falta para corregirlo o borrarlo."""
    try:
        f = notion.pagina(page_id)
    except (NotionError, KeyError):
        return None
    if not f or f.get("Tipo") is None and f.get("Monto") is None:
        return None
    monto, moneda = float(f.get("Monto") or 0), f.get("Moneda") or "PEN"
    monto_s = f.get("Monto S/")
    return {"id": f.get("_id") or page_id, "tipo": f.get("Tipo") or "Gasto",
            "categoria": f.get("Categoría") or "Otros", "descripcion": f.get("Descripción") or "",
            "monto": monto, "moneda": moneda,
            "monto_s": float(monto_s if monto_s is not None else soles(monto, moneda)),
            "medio": f.get("Medio de pago"), "tarjeta": f.get("Tarjeta"), "cuenta": f.get("Cuenta"),
            "frecuencia": f.get("Frecuencia"), "fecha": (f.get("Fecha") or "")[:10],
            "cuotas": int(f.get("Cuotas")) if f.get("Cuotas") else None}


def mueve_cuenta(mov: dict) -> bool:
    """Si ese movimiento sube o baja el saldo de un banco. Una compra a credito no: va a la deuda."""
    return bool(mov.get("medio")) and (mov["tipo"] == "Ingreso" or
                                      (mov["tipo"] == "Gasto" and mov.get("tarjeta") != "Crédito"))


def va_a_tarjeta(mov: dict) -> bool:
    return mov["tipo"] == "Gasto" and mov.get("tarjeta") == "Crédito"


def delta_cuenta(mov: dict) -> float:
    """Lo que ese movimiento le hace al saldo: un ingreso suma, un gasto resta."""
    return mov["monto"] if mov["tipo"] == "Ingreso" else -mov["monto"]


def corregir_monto(notion, page_id: str, monto: float, moneda: str) -> dict:
    """Cambia el monto (y la moneda) de un movimiento ya guardado, con sus columnas en S/, USD y RUB."""
    tc = tipo_de_cambio(moneda)
    return notion.editar_pagina(page_id, {
        "Monto": p_number(monto), "Moneda": p_select(moneda), "Tipo de cambio": p_number(tc),
        "Monto S/": p_number(monto * tc), "Monto USD": p_number(en_dolares(monto * tc)),
        "Monto RUB": p_number(en_rublos(monto * tc))})


# ---------------------------------------------------------------- resumen

@dataclass
class Resumen:
    periodo: Periodo
    ingresos: float = 0.0
    gastos: float = 0.0
    ahorro: float = 0.0
    inversion: float = 0.0
    por_categoria: dict = field(default_factory=dict)       # gastos
    anuales: dict = field(default_factory=dict)             # de esos, los pagos anuales (no cuentan contra el tope mensual)
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

    @property
    def mensuales(self) -> dict:
        """Gastos por categoria sin los pagos anuales: lo que se compara con el presupuesto mensual."""
        return {c: round(v - self.anuales.get(c, 0), 2) for c, v in self.por_categoria.items()
                if round(v - self.anuales.get(c, 0), 2) > 0}

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
        elif m["tipo"] == "Inversión" or m.get("cuenta") == "Inversión":
            # en el formulario de gastos, la cuenta "Inversion" era plata para el depa: no es gasto
            r.inversion += v
        else:
            r.gastos += v
            r.por_categoria[m["categoria"]] = r.por_categoria.get(m["categoria"], 0) + v
            if m.get("frecuencia") == "Anual":
                r.anuales[m["categoria"]] = r.anuales.get(m["categoria"], 0) + v
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

def presupuesto(notion, bases: dict, columna: str = "Mensual S/") -> dict:
    """{categoria: tope en soles}. Mensual por defecto; columna="Anual S/" da los topes de los pagos anuales."""
    if PRESUPUESTO not in bases:
        return {}
    out = {}
    for f in notion.consultar(bases[PRESUPUESTO], limite=200):
        if f.get("Categoría") and f.get(columna):
            out[f["Categoría"]] = float(f[columna])
    return out


def presupuesto_anual(notion, bases: dict) -> dict:
    return presupuesto(notion, bases, "Anual S/")


def pagado_anual(notion, bases: dict, categoria: str, d: Optional[date] = None) -> float:
    """Lo pagado en el año como pago anual en esa categoria."""
    d = d or hoy()
    return round(sum(m["monto_s"] for m in movimientos(notion, bases, date(d.year, 1, 1), d)
                     if m["tipo"] == "Gasto" and m["categoria"] == categoria and m.get("frecuencia") == "Anual"), 2)


def fijar_presupuesto(notion, bases: dict, categoria: str, monto: float, columna: str = "Mensual S/") -> dict:
    existentes = notion.consultar(bases[PRESUPUESTO], {"property": "Categoría", "title": {"equals": categoria}}, limite=5)
    props = {"Categoría": p_title(categoria), columna: p_number(monto), "Grupo": p_select(C.grupo(categoria))}
    if existentes:
        return notion.editar_pagina(existentes[0]["_id"], props)
    return notion.crear_pagina(bases[PRESUPUESTO], props)


def fuera_de_presupuesto(categoria: str, plan: dict, frecuencia: Optional[str] = None, anual: Optional[dict] = None) -> bool:
    """Un gasto que no estaba previsto: su categoria no tiene tope (mensual, o anual si es pago anual).
    Las categorias del dia a dia sin tope no cuentan si hay /limite: ya las controla el limite."""
    if frecuencia == "Anual":
        return categoria not in (anual or {})
    if not plan or categoria in plan:
        return False
    return categoria in C.CATEGORIAS_FIJAS or not limite()


def gastos_fuera(r: "Resumen", plan: dict, anual: Optional[dict] = None) -> dict:
    """{categoria: soles} de lo gastado en el periodo fuera del presupuesto."""
    out = {}
    for cat, v in r.mensuales.items():
        if fuera_de_presupuesto(cat, plan):
            out[cat] = round(v, 2)
    for cat, v in r.anuales.items():
        if fuera_de_presupuesto(cat, plan, "Anual", anual):
            out[cat] = round(out.get(cat, 0) + v, 2)
    return out


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
    """Cuentas y bienes de Patrimonio mas las deudas activas de Deudas (como Pasivo)."""
    out = [{"id": d["id"], "nombre": d["deuda"], "clase": "Pasivo", "tipo": d["tipo"], "valor": d["saldo"],
            "moneda": d["moneda"], "valor_s": d["saldo_s"], "actualizado": d["actualizado"], "tasa": d["tasa"]}
           for d in deudas(notion, bases) if d["saldo_s"] > 0]
    if PATRIMONIO not in bases:
        return out
    for f in notion.consultar(bases[PATRIMONIO], limite=300):
        # como en Deudas: lo que vale es Valor y Moneda (se pueden editar a mano en Notion);
        # Valor S/ se recalcula con el cambio del dia y se corrige en Notion si quedo distinto
        valor_s = soles(f.get("Valor") or 0, f.get("Moneda") or "PEN")
        if f.get("Valor S/") is None or abs(float(f["Valor S/"]) - valor_s) > 0.01:
            try:
                notion.editar_pagina(f["_id"], {"Valor S/": p_number(valor_s)})
            except NotionError:
                pass
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


def cuentas(notion, bases: dict) -> list:
    """Las cuentas de dinero (Activo, Efectivo y bancos) de Patrimonio."""
    if PATRIMONIO not in bases:
        return []
    return [{"id": f["_id"], "nombre": f.get("Nombre") or "?", "valor": float(f.get("Valor") or 0),
             "moneda": f.get("Moneda") or "PEN"}
            for f in notion.consultar(bases[PATRIMONIO], limite=300)
            if (f.get("Clase") or "Activo") == "Activo" and (f.get("Tipo") or "Efectivo y bancos") in C.LIQUIDOS]


def buscar_cuenta(notion, bases: dict, medio: Optional[str], moneda: str) -> Optional[dict]:
    """La cuenta de ese banco en esa moneda: medio Interbank + USD -> "Interbank dólares". Plin y Yape van a su banco."""
    if not medio:
        return None
    m = C.normal(C.BILLETERA_BANCO.get(medio, medio))   # Plin y Yape -> Interbank
    for c in cuentas(notion, bases):
        if c["moneda"] == moneda and (C.normal(c["nombre"]) == m or m in C.normal(c["nombre"]).split()):
            return c
    return None


def mover_cuenta(notion, cuenta: dict, delta: float) -> float:
    """Suma (o resta) al saldo de una cuenta, en su moneda. Devuelve el saldo nuevo."""
    nuevo = round(cuenta["valor"] + delta, 2)
    notion.editar_pagina(cuenta["id"], {"Valor": p_number(nuevo), "Valor S/": p_number(soles(nuevo, cuenta["moneda"])),
                                        "Actualizado": p_date(hoy())})
    return nuevo


def nombre_efectivo(moneda: str) -> str:
    """La cuenta de la billetera en cada moneda: "Efectivo", "Efectivo dólares", "Efectivo rublos"."""
    return "Efectivo" if moneda == "PEN" else "Efectivo " + {"USD": "dólares", "RUB": "rublos", "EUR": "euros"}.get(moneda, moneda)


def es_efectivo(cuenta: dict) -> bool:
    return C.normal(cuenta["nombre"]).split()[:1] == ["efectivo"]


def retirar_efectivo(notion, bases: dict, cuenta: dict, monto: float) -> tuple:
    """Saca plata de un banco y la pasa al efectivo de la misma moneda (no es un gasto: el patrimonio no cambia).
    Crea la cuenta de efectivo si no existe. Devuelve (saldo del banco, cuenta de efectivo, saldo del efectivo)."""
    banco = mover_cuenta(notion, cuenta, -monto)
    nombre = nombre_efectivo(cuenta["moneda"])
    ef = next((c for c in cuentas(notion, bases)
               if c["moneda"] == cuenta["moneda"] and C.normal(c["nombre"]) == C.normal(nombre)), None)
    if ef:
        return banco, ef, mover_cuenta(notion, ef, monto)
    pag, _ = fijar_patrimonio(notion, bases, nombre, "Activo", "Efectivo y bancos", monto, cuenta["moneda"])
    return banco, {"id": pag["id"], "nombre": nombre, "valor": monto, "moneda": cuenta["moneda"]}, monto


# ---------------------------------------------------------------- recordatorios y pagos del mes

def dia_del_mes(dia: int, d: date) -> int:
    """El dia 30 en febrero es el ultimo dia del mes."""
    return min(int(dia), monthrange(d.year, d.month)[1])


def proxima_fecha(dia: Optional[int], ultimo: str, d: Optional[date] = None) -> Optional[date]:
    """La fecha que va en el calendario de Notion: este mes, o el que viene si ya se hizo este mes."""
    if not dia:
        return None
    d = d or hoy()
    base = d if not (ultimo and ultimo[:7] == d.isoformat()[:7]) else sumar_meses(d.replace(day=1), 1)
    return base.replace(day=dia_del_mes(dia, base))


def recordatorios(notion, bases: dict) -> list:
    if RECORDATORIOS not in bases:
        return []
    out = []
    for f in notion.consultar(bases[RECORDATORIOS], limite=200):
        if (f.get("Estado") or "Activo") != "Activo":
            continue
        prox = proxima_fecha(int(f["Día"]) if f.get("Día") else None, (f.get("Último") or "")[:10])
        if prox and (f.get("Próxima fecha") or "")[:10] != prox.isoformat():
            try:
                notion.editar_pagina(f["_id"], {"Próxima fecha": p_date(prox)})   # el calendario de Notion al dia
            except NotionError:
                pass
        out.append({"id": f["_id"], "nombre": f.get("Recordatorio") or "?", "dia": int(f["Día"]) if f.get("Día") else None,
                    "tipo": f.get("Tipo") or "Otro", "monto": float(f["Monto"]) if f.get("Monto") else None,
                    "moneda": f.get("Moneda") or "PEN", "categoria": f.get("Categoría"), "deuda": f.get("Deuda") or "",
                    "ultimo": (f.get("Último") or "")[:10]})
    return sorted(out, key=lambda r: (r["dia"] or 99, r["nombre"]))


def hecho_este_mes(r: dict, d: Optional[date] = None) -> bool:
    d = d or hoy()
    return bool(r["ultimo"]) and r["ultimo"][:7] == d.isoformat()[:7]


def pendientes_del_mes(notion, bases: dict, d: Optional[date] = None) -> list:
    d = d or hoy()
    return [r for r in recordatorios(notion, bases) if not hecho_este_mes(r, d)]


def avisos_de_hoy(notion, bases: dict, d: Optional[date] = None) -> list:
    """Los recordatorios que tocan hoy (o que se pospusieron para hoy) y aun no se hicieron."""
    d = d or hoy()
    pospuestos = ajustes().get("posponer", {})
    out = []
    for r in pendientes_del_mes(notion, bases, d):
        pospuesto = pospuestos.get(r["id"])
        if pospuesto and pospuesto > d.isoformat():
            continue                                   # lo pidio para mañana
        toca = r["dia"] and dia_del_mes(r["dia"], d) == d.day
        if toca or pospuesto == d.isoformat():
            out.append(r)
    return out


def marcar_hecho(notion, r: dict, d: Optional[date] = None) -> None:
    d = d or hoy()
    props = {"Último": p_date(d)}
    prox = proxima_fecha(r["dia"], d.isoformat(), d)
    if prox:
        props["Próxima fecha"] = p_date(prox)                  # pasa al mes que viene en el calendario
    notion.editar_pagina(r["id"], props)


def posponer(rid: str, d: Optional[date] = None) -> date:
    manana = (d or hoy()) + timedelta(days=1)
    a = ajustes()
    a.setdefault("posponer", {})[rid] = manana.isoformat()
    _guardar_ajustes(a)
    return manana


def proyeccion(notion, bases: dict, d: Optional[date] = None) -> Optional[dict]:
    """Como cierra el mes si no entra mas dinero: lo que ya entro y salio, los pagos fijos que faltan
    (Recordatorios con monto) y el dia a dia de los dias que quedan (el limite, o el promedio)."""
    d = d or hoy()
    m = mes(d)
    movs = movimientos(notion, bases, m.desde, d)
    r = resumir(movs, m)
    if r.cantidad == 0 and not recordatorios(notion, bases):
        return None
    dias_rest = (m.hasta - d).days
    lim = limite()
    if lim:
        diario = lim[0] * tipo_de_cambio(lim[1])
    else:
        diario = sum(x["monto_s"] for x in movs if es_dia_a_dia(x)) / max(d.day, 1)
    fijos = sum(soles(x["monto"], x["moneda"]) for x in pendientes_del_mes(notion, bases, d)
                if x["monto"] and x["tipo"] in ("Pago", "Deuda"))
    resto = round(diario * dias_rest, 2)
    return {"ingresos": r.ingresos, "gastos": r.gastos, "ahorro": r.ahorro, "fijos": round(fijos, 2),
            "dia_a_dia": resto, "dias": dias_rest,
            "cierre": round(r.ingresos - r.gastos - r.ahorro - fijos - resto, 2)}


# ---------------------------------------------------------------- plan para salir de deudas

def plan_deudas(lista: list, extra_s: float = 0.0, maximo: int = 120) -> dict:
    """Simula mes a mes: cada deuda paga su cuota (o lo que le quede) con su interes si se sabe la
    tasa; el extra, y las cuotas que se liberan al terminar una deuda, van a la deuda con mas
    interes (o a la mas chica si no hay tasas). Todo en soles."""
    ds = [{"deuda": x["deuda"], "saldo": x["saldo_s"], "cuota": soles(x["cuota"], x["moneda"]) if x.get("cuota") else 0.0,
           "tasa": float(x.get("tasa") or 0)} for x in lista if x["saldo_s"] > 0]
    orden_extra = sorted(ds, key=lambda x: (-x["tasa"], x["saldo"])) if any(x["tasa"] for x in ds) \
        else sorted(ds, key=lambda x: x["saldo"])
    presupuesto_mes = sum(x["cuota"] for x in ds) + extra_s
    fin, intereses, mes_n = {}, 0.0, 0
    while any(x["saldo"] > 0.005 for x in ds) and mes_n < maximo:
        mes_n += 1
        for x in ds:
            if x["saldo"] > 0:
                i = x["saldo"] * x["tasa"] / 12
                x["saldo"] += i
                intereses += i
        disponible = presupuesto_mes
        for x in ds:                                   # primero la cuota de cada una
            if x["saldo"] > 0 and x["cuota"]:
                pago = min(x["cuota"], x["saldo"], disponible)
                x["saldo"] -= pago
                disponible -= pago
        for x in orden_extra:                          # lo que sobra, a la que toca
            if disponible <= 0:
                break
            if x["saldo"] > 0:
                pago = min(x["saldo"], disponible)
                x["saldo"] -= pago
                disponible -= pago
        for x in ds:
            if x["saldo"] <= 0.005 and x["deuda"] not in fin:
                fin[x["deuda"]] = mes_n
        if presupuesto_mes <= 0:
            break
    sin_pagar = [x["deuda"] for x in ds if x["saldo"] > 0.005]
    return {"meses": mes_n if not sin_pagar else None, "fin": fin, "orden": [x["deuda"] for x in orden_extra],
            "intereses": round(intereses, 2), "por_mes": round(presupuesto_mes, 2), "sin_pagar": sin_pagar}


# ---------------------------------------------------------------- tipo de cambio: buen momento

def alerta_cambio(umbral: float = 0.03) -> Optional[str]:
    """Si hoy el dolar esta bastante mas alto o mas bajo que su promedio de 30 dias (en rublos y en soles)."""
    h = ajustes().get("historial_tc", {})
    dias = sorted(h)
    if len(dias) < 10:
        return None
    hoy_ = h[dias[-1]]
    previos = [h[x] for x in dias[-31:-1]]
    out = []
    for nombre, valor in (("rublos", lambda v: v["USD"] / v["RUB"]), ("soles", lambda v: v["USD"])):
        actual = valor(hoy_)
        prom = sum(valor(v) for v in previos) / len(previos)
        dif = (actual - prom) / prom
        simbolo = "₽" if nombre == "rublos" else "S/"
        if dif >= umbral:
            out.append("💱 El dólar está alto en %s: %s %.2f (promedio del mes %s %.2f, +%.1f%%). Buen momento para cambiar dólares a %s."
                       % (nombre, simbolo, actual, simbolo, prom, dif * 100, nombre))
        elif dif <= -umbral:
            out.append("💱 El dólar está barato en %s: %s %.2f (promedio del mes %s %.2f, %.1f%%). Buen momento para comprar dólares."
                       % (nombre, simbolo, actual, simbolo, prom, dif * 100))
    return "\n".join(out) or None


# ---------------------------------------------------------------- suscripciones

CATEGORIA_SUSCRIPCIONES = "Suscripciones"


def sumar_meses(d: date, n: int) -> date:
    m = d.month - 1 + n
    anio, mes_ = d.year + m // 12, m % 12 + 1
    return date(anio, mes_, min(d.day, monthrange(anio, mes_)[1]))


def cada_texto(cada: int) -> str:
    return {1: "mensual", 12: "anual"}.get(cada, "cada %d meses" % cada)


def suscripciones(notion, bases: dict, todas: bool = False) -> list:
    """Las suscripciones activas: nombre, monto, moneda, cada cuantos meses y proximo pago."""
    if SUSCRIPCIONES not in bases:
        return []
    out = []
    for f in notion.consultar(bases[SUSCRIPCIONES], limite=200):
        estado = f.get("Estado") or "Activa"
        if estado != "Activa" and not todas:
            continue
        cada = int(f.get("Cada (meses)") or 1)
        monto, moneda = float(f.get("Monto") or 0), f.get("Moneda") or "PEN"
        out.append({"id": f["_id"], "nombre": f.get("Suscripción") or "?", "monto": monto, "moneda": moneda,
                    "cada": max(cada, 1), "por_mes_s": round(soles(monto, moneda) / max(cada, 1), 2),
                    "ultimo": f.get("Último pago"), "proximo": f.get("Próximo pago"), "estado": estado})
    return sorted(out, key=lambda x: (x["proximo"] or "9999", x["nombre"]))


def buscar_suscripcion(lista: list, texto: str) -> Optional[dict]:
    """La suscripcion que nombra el texto: 'claude pro mayo' -> Claude Pro."""
    t = C.normal(texto)
    palabras = set(t.split())
    for s_ in lista:
        n = C.normal(s_["nombre"])
        if n == t or n in t or (n.split() and n.split()[0] in palabras and len(n.split()[0]) > 2):
            return s_
    return None


def registrar_pago_suscripcion(notion, bases: dict, nombre: str, monto: float, moneda: str, cada: int,
                               fecha: date, existente: Optional[dict] = None) -> dict:
    """Crea la suscripcion (o anota el pago de una que ya existe) y deja el proximo pago calculado."""
    proximo = sumar_meses(fecha, cada)
    props = {"Monto": p_number(monto), "Moneda": p_select(moneda), "Cada (meses)": p_number(cada),
             "Por mes S/": p_number(round(soles(monto, moneda) / cada, 2)), "Último pago": p_date(fecha),
             "Próximo pago": p_date(proximo), "Estado": p_select("Activa")}
    if existente:
        notion.editar_pagina(existente["id"], props)
        pid = existente["id"]
    else:
        props["Suscripción"] = p_title(nombre)
        pid = notion.crear_pagina(bases[SUSCRIPCIONES], props)["id"]
    return {"id": pid, "nombre": existente["nombre"] if existente else nombre, "cada": cada, "proximo": proximo}


def recalcular_presupuesto_suscripciones(notion, bases: dict) -> dict:
    """Cuanto suman las suscripciones: las mensuales, las de varios meses en un año, y todo junto por mes.
    El tope anual de Suscripciones se ajusta a la lista; el mensual es el maximo que fijo la persona
    (/presupuesto suscripciones 500) y se compara con el total por mes."""
    lista = suscripciones(notion, bases)
    mensual = round(sum(soles(x["monto"], x["moneda"]) for x in lista if x["cada"] == 1), 2)
    anual = round(sum(soles(x["monto"], x["moneda"]) * 12 / x["cada"] for x in lista if x["cada"] > 1), 2)
    if PRESUPUESTO in bases and anual:
        fijar_presupuesto(notion, bases, CATEGORIA_SUSCRIPCIONES, anual, "Anual S/")
    tope = presupuesto(notion, bases).get(CATEGORIA_SUSCRIPCIONES) if PRESUPUESTO in bases else None
    return {"mensual": mensual, "anual": anual, "por_mes": round(mensual + anual / 12, 2), "tope": tope}


def renovaciones(notion, bases: dict, d: Optional[date] = None, dias: int = 3) -> list:
    """Suscripciones que se renuevan entre hoy y dentro de `dias` dias."""
    d = d or hoy()
    lim = (d + timedelta(days=dias)).isoformat()
    return [x for x in suscripciones(notion, bases) if x["proximo"] and d.isoformat() <= x["proximo"][:10] <= lim]


# ---------------------------------------------------------------- deudas

def deudas(notion, bases: dict, todas: bool = False, con_cuotas: bool = True) -> list:
    """Deudas de la base Deudas, la mas grande primero. Sin todas=True solo las activas.

    Las deudas se pueden editar a mano en Notion: lo que vale es Saldo y Moneda. Saldo S/
    se recalcula aqui y, si quedo distinto (o falta), se corrige en Notion para que el
    grafico muestre lo mismo. Una deuda Activa con Saldo 0 pasa a Pagada."""
    if DEUDAS not in bases:
        return []
    out = []
    for f in notion.consultar(bases[DEUDAS], limite=200):
        saldo, moneda = float(f.get("Saldo") or 0), f.get("Moneda") or "PEN"
        saldo_s = round(soles(saldo, moneda), 2)
        estado = f.get("Estado") or "Activa"
        if estado == "Activa" and saldo <= 0 and f.get("Saldo") is not None:
            estado = "Pagada"
        cambios = {}
        for col, valor in (("Saldo S/", saldo_s), ("Saldo USD", en_dolares(saldo_s)), ("Saldo RUB", en_rublos(saldo_s))):
            guardado = f.get(col)
            if guardado is None or abs(float(guardado) - valor) > 0.01:
                cambios[col] = p_number(valor)
        if estado != f.get("Estado"):
            cambios["Estado"] = p_select(estado)
        if cambios:
            try:
                notion.editar_pagina(f["_id"], cambios)
            except NotionError:
                pass   # se corrige la proxima vez; el calculo de ahora ya usa el valor bueno
        if estado != "Activa" and not todas:
            continue
        out.append({"id": f["_id"], "deuda": f.get("Deuda") or "?", "tipo": f.get("Tipo") or "Otra",
                    "saldo": saldo, "moneda": moneda, "saldo_s": saldo_s,
                    "original": f.get("Monto original"), "tasa": f.get("Tasa anual"),
                    "cuota": f.get("Cuota mensual"), "dia": f.get("Día de pago"),
                    "estado": estado, "actualizado": f.get("Actualizado")})
    if con_cuotas:
        # la cuota de una tarjeta la dicen sus compras en cuotas, no un numero que se queda viejo.
        # Sin compras en cuotas vale lo que el usuario haya puesto a mano en Notion.
        por_deuda = cuotas_por_deuda(compras_en_cuotas(notion, bases))
        for d in out:
            if d["deuda"] in por_deuda:
                d["cuota"] = round(por_deuda[d["deuda"]] / tipo_de_cambio(d["moneda"]), 2)
    return sorted(out, key=lambda d: -d["saldo_s"])


def buscar_deuda(lista: list, texto: str) -> Optional[dict]:
    t = C.normal(texto).strip()
    if not t:
        return None
    for d in lista:
        if C.normal(d["deuda"]) == t:
            return d
    for d in lista:
        if t in C.normal(d["deuda"]) or C.normal(d["deuda"]) in t:
            return d
    return None


def fijar_deuda(notion, bases: dict, nombre: str, tipo: str, saldo: float, moneda: str = "PEN") -> tuple:
    """Crea la deuda o actualiza su saldo. Devuelve (pagina, saldo anterior en soles o None)."""
    existente = buscar_deuda(deudas(notion, bases, todas=True), nombre)
    props = {"Saldo": p_number(saldo), "Moneda": p_select(moneda), "Saldo S/": p_number(soles(saldo, moneda)),
             "Estado": p_select("Activa" if saldo > 0 else "Pagada"), "Actualizado": p_date(hoy())}
    if existente:
        return notion.editar_pagina(existente["id"], props), existente["saldo_s"]
    props.update({"Deuda": p_title(nombre), "Tipo": p_select(tipo), "Monto original": p_number(saldo),
                  "Inicio": p_date(hoy())})
    return notion.crear_pagina(bases[DEUDAS], props), None


def cargar_a_tarjeta(notion, bases: dict, medio: str, monto: float, moneda: str) -> dict:
    """Una compra a credito: suma el monto a la deuda de esa tarjeta, y la crea si no existe.
    Devuelve la deuda como quedo, con "cargo" = lo sumado en la moneda de la deuda y "nueva"."""
    nombre = C.deuda_de_tarjeta(medio)
    existente = next((d for d in deudas(notion, bases, todas=True) if C.normal(d["deuda"]) == C.normal(nombre)), None)
    if not existente:
        props = {"Deuda": p_title(nombre), "Tipo": p_select("Tarjeta de crédito"),
                 "Acreedor": p_text(C.BANCO_TARJETA.get(medio, medio)), "Monto original": p_number(monto),
                 "Saldo": p_number(monto), "Moneda": p_select(moneda), "Saldo S/": p_number(soles(monto, moneda)),
                 "Inicio": p_date(hoy()), "Estado": p_select("Activa"), "Actualizado": p_date(hoy())}
        pag = notion.crear_pagina(bases[DEUDAS], props)
        return {"id": pag["id"], "deuda": nombre, "saldo": round(monto, 2), "moneda": moneda,
                "cargo": round(monto, 2), "nueva": True}
    cargo = monto if moneda == existente["moneda"] else soles(monto, moneda) / tipo_de_cambio(existente["moneda"])
    nuevo = round(existente["saldo"] + cargo, 2)
    notion.editar_pagina(existente["id"], {
        "Saldo": p_number(nuevo), "Saldo S/": p_number(soles(nuevo, existente["moneda"])),
        "Estado": p_select("Activa"), "Actualizado": p_date(hoy())})
    return {"id": existente["id"], "deuda": existente["deuda"], "saldo": nuevo, "moneda": existente["moneda"],
            "cargo": round(cargo, 2), "nueva": False}


def primer_mes_de_cuota(compra: date) -> date:
    """El mes en que se paga la primera cuota: el siguiente al de la compra."""
    return date(compra.year + 1, 1, 1) if compra.month == 12 else date(compra.year, compra.month + 1, 1)


def mes_texto(d: date) -> str:
    """'noviembre' si es de este año, 'enero de 2027' si no."""
    nombre = MESES[d.month - 1]
    return nombre if d.year == hoy().year else "%s de %d" % (nombre, d.year)


def compras_en_cuotas(notion, bases: dict, d: Optional[date] = None) -> list:
    """Las compras a credito en cuotas que todavia se estan pagando en el mes de d.

    La primera cuota cae el mes siguiente a la compra: una de 6 cuotas hecha en octubre se paga
    de noviembre a abril. "toca" es la cuota de este mes (0 = la compra es de este mes y la
    primera cae el que viene) y "faltan" las que quedan por pagar contando la de este mes.
    Como sale de los movimientos, cuando la compra termina deja de contar sola."""
    if MOVIMIENTOS not in bases:
        return []
    d = d or hoy()
    desde = date(d.year - 6, d.month, 1)   # 72 cuotas es el maximo que acepta el bot
    filtro = {"and": [{"property": "Fecha", "date": {"on_or_after": desde.isoformat()}},
                      {"property": "Fecha", "date": {"on_or_before": d.isoformat()}}]}
    out = []
    for f in notion.consultar(bases[MOVIMIENTOS], filtro, limite=5000):
        n = int(f.get("Cuotas") or 0)
        if n < 2 or f.get("Tarjeta") != "Crédito" or (f.get("Tipo") or "Gasto") != "Gasto" or not f.get("Medio de pago"):
            continue
        try:
            compra = date.fromisoformat((f.get("Fecha") or "")[:10])
        except ValueError:
            continue
        toca = (d.year - compra.year) * 12 + d.month - compra.month   # 1 = la primera cuota
        if not 0 <= toca <= n:
            continue
        monto, moneda = float(f.get("Monto") or 0), f.get("Moneda") or "PEN"
        out.append({"deuda": C.deuda_de_tarjeta(f["Medio de pago"]), "tarjeta": f["Medio de pago"],
                    "descripcion": f.get("Descripción") or "", "cuotas": n, "toca": toca,
                    "faltan": min(n, n - toca + 1), "cuota": round(monto / n, 2), "moneda": moneda,
                    "cuota_s": round(soles(monto, moneda) / n, 2), "fecha": compra,
                    "primera": primer_mes_de_cuota(compra)})
    return sorted(out, key=lambda x: -x["cuota_s"])


def cuotas_por_deuda(compras: list) -> dict:
    """{nombre de la deuda: lo que toca pagar este mes por sus compras en cuotas, en S/}"""
    out = {}
    for c in compras:
        out[c["deuda"]] = round(out.get(c["deuda"], 0) + c["cuota_s"], 2)
    return out


def deuda_de_tarjeta(notion, bases: dict, medio: Optional[str]) -> Optional[dict]:
    """La deuda de esa tarjeta, si ya existe (para deshacer una compra a credito vieja)."""
    if not medio or DEUDAS not in bases:
        return None
    nombre = C.deuda_de_tarjeta(medio)
    return next((d for d in deudas(notion, bases, todas=True, con_cuotas=False)
                 if C.normal(d["deuda"]) == C.normal(nombre)), None)


def pagar_deuda(notion, deuda: dict, monto: float, moneda: Optional[str] = None) -> float:
    """Baja el saldo con un pago (en la moneda de la deuda si no se dice otra). Devuelve el saldo nuevo."""
    moneda = moneda or deuda["moneda"]
    pago = monto if moneda == deuda["moneda"] else soles(monto, moneda) / tipo_de_cambio(deuda["moneda"])
    nuevo = round(max(deuda["saldo"] - pago, 0), 2)
    notion.editar_pagina(deuda["id"], {
        "Saldo": p_number(nuevo), "Saldo S/": p_number(soles(nuevo, deuda["moneda"])),
        "Estado": p_select("Activa" if nuevo > 0 else "Pagada"), "Actualizado": p_date(hoy())})
    return nuevo


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
    for cat, g, tope, usado in estado_presupuesto(r.mensuales, plan, avance_mes):
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
        con_tasa = [i for i in items if i["clase"] == "Pasivo" and i.get("tasa") and i["valor_s"] > 0]
        if len(con_tasa) > 1:
            cara = max(con_tasa, key=lambda i: i["tasa"])
            out.append("❄️ Método avalancha: paga el mínimo en todas y lo extra a %s (%s al año), la deuda más cara." % (cara["nombre"], pct(cara["tasa"])))
        if act > 0 and pas / act > 0.5:
            out.append("⚠️ Tus deudas son el %s de lo que tienes. Prioriza bajarlas antes de nuevas compras grandes." % pct(pas / act))
    return out
