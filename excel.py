"""Un Excel con todo y sus graficos, para ver las finanzas sin depender de los graficos de Notion
(el plan gratis de Notion solo deja uno). El bot lo manda por Telegram con /excel.

Hojas: Resumen, Deudas, Cuentas, Metas, Presupuesto, Por mes, Categorias y Movimientos del año.
Cada monto va en soles, dolares y rublos con el tipo de cambio del dia.
"""
from collections import defaultdict
from datetime import date
from io import BytesIO
from typing import Optional

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

import categorias as C
import finanzas as F

TITULO = Font(bold=True, size=14)
NEGRITA = Font(bold=True, color="FFFFFF")
CABECERA = PatternFill("solid", fgColor="2F5597")
SOLES = '"S/" #,##0.00'
DOLARES = '"$" #,##0.00'
RUBLOS = '"₽" #,##0'
PORCENTAJE = "0%"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _tabla(ws, fila: int, columnas: list, filas: list, formatos: Optional[dict] = None) -> int:
    """Escribe una tabla con cabecera azul desde `fila`. Devuelve la ultima fila escrita."""
    formatos = formatos or {}
    for j, nombre in enumerate(columnas, 1):
        c = ws.cell(row=fila, column=j, value=nombre)
        c.font, c.fill, c.alignment = NEGRITA, CABECERA, Alignment(horizontal="center")
    for i, valores in enumerate(filas, fila + 1):
        for j, v in enumerate(valores, 1):
            c = ws.cell(row=i, column=j, value=v)
            if columnas[j - 1] in formatos:
                c.number_format = formatos[columnas[j - 1]]
    for j, nombre in enumerate(columnas, 1):
        largo = max([len(str(nombre))] + [len("{:,.2f}".format(f[j - 1]) if isinstance(f[j - 1], float) else str(f[j - 1] or "")) for f in filas])
        ws.column_dimensions[get_column_letter(j)].width = min(max(largo + 3, 10), 45)
    return fila + len(filas)


def _tres(soles_: float) -> tuple:
    return round(soles_, 2), F.en_dolares(soles_), F.en_rublos(soles_)


TRES = {"S/": SOLES, "$": DOLARES, "₽": RUBLOS}


def _grafico(ws, tipo, titulo: str, datos: tuple, categorias: tuple, ancla: str, alto: float = 8, ancho: float = 16):
    """datos/categorias: (col_min, fila_min, col_max, fila_max) en la hoja; los datos incluyen la cabecera."""
    g = {"barra": BarChart, "columna": BarChart, "torta": PieChart, "linea": LineChart}[tipo]()
    if tipo == "barra":
        g.type = "bar"
    g.title = titulo
    g.height, g.width = alto, ancho
    c1, f1, c2, f2 = datos
    g.add_data(Reference(ws, min_col=c1, min_row=f1, max_col=c2, max_row=f2), titles_from_data=True)
    c1, f1, c2, f2 = categorias
    g.set_categories(Reference(ws, min_col=c1, min_row=f1, max_col=c2, max_row=f2))
    if tipo == "torta":
        g.dataLabels = DataLabelList()
        g.dataLabels.showPercent = True
    ws.add_chart(g, ancla)


def libro(notion, bases: dict, hoy: Optional[date] = None) -> bytes:
    hoy = hoy or F.hoy()
    anio = date(hoy.year, 1, 1)
    mes = F.mes(hoy)
    movs = F.movimientos(notion, bases, anio, hoy) if F.MOVIMIENTOS in bases else []
    r_mes = F.resumir([m for m in movs if m["fecha"] >= mes.desde.isoformat()], mes)
    r_anio = F.resumir(movs, F.Periodo("Anual", anio, hoy))
    deudas = F.deudas(notion, bases)
    cuentas = [i for i in F.patrimonio(notion, bases) if i["clase"] == "Activo"]
    metas = F.metas(notion, bases)
    plan = F.presupuesto(notion, bases)
    activos = sum(i["valor_s"] for i in cuentas)
    pasivos = sum(d["saldo_s"] for d in deudas)

    wb = Workbook()

    # ---- Resumen
    ws = wb.active
    ws.title = "Resumen"
    ws["A1"] = "Mis finanzas al %s" % hoy.strftime("%d/%m/%Y")
    ws["A1"].font = TITULO
    ws["A2"] = "Tipo de cambio: 1 dólar = S/ %s · 1 rublo = S/ %s · 1 dólar = ₽ %s" % (
        F.tipo_de_cambio("USD"), F.tipo_de_cambio("RUB"), round(F.tipo_de_cambio("USD") / F.tipo_de_cambio("RUB"), 2))
    filas = [("🏦 Lo que tienes",) + _tres(activos), ("💳 Lo que debes",) + _tres(pasivos),
             ("📊 Patrimonio neto",) + _tres(activos - pasivos), ("", None, None, None),
             ("💰 Ingresos de %s" % F.MESES[hoy.month - 1],) + _tres(r_mes.ingresos),
             ("💸 Gastos de %s" % F.MESES[hoy.month - 1],) + _tres(r_mes.gastos),
             ("🐷 Ahorro de %s" % F.MESES[hoy.month - 1],) + _tres(r_mes.ahorro),
             ("⚖️ Balance de %s" % F.MESES[hoy.month - 1],) + _tres(r_mes.balance), ("", None, None, None),
             ("💰 Ingresos %d" % hoy.year,) + _tres(r_anio.ingresos), ("💸 Gastos %d" % hoy.year,) + _tres(r_anio.gastos),
             ("⚖️ Balance %d" % hoy.year,) + _tres(r_anio.balance)]
    _tabla(ws, 4, ["Concepto", "S/", "$", "₽"], filas, TRES)
    ws.column_dimensions["A"].width = 28
    _grafico(ws, "columna", "Tienes vs debes (S/)", (2, 4, 2, 6), (1, 5, 1, 6), "F4", alto=7, ancho=12)

    # limite del dia a dia (/limite): cuanto se puede gastar y cuanto va
    lim = F.estado_limite(notion, bases, hoy)
    if lim:
        tc = F.tipo_de_cambio(lim["moneda"])
        fila = 4 + len(filas) + 3
        ws.cell(row=fila - 1, column=1, value="📏 Día a día (sin gastos fijos del mes)").font = Font(bold=True)
        filas_lim = []
        for k, nombre in (("dia", "Hoy"), ("semana", "Esta semana"), ("mes", "Este mes")):
            x = lim[k]
            filas_lim.append((nombre,) + _tres(x["tope"] * tc) + _tres(x["gastado"] * tc) + _tres(x["queda"] * tc))
        _tabla(ws, fila, ["Período", "Puedes S/", "Puedes $", "Puedes ₽", "Gastado S/", "Gastado $", "Gastado ₽",
                          "Queda S/", "Queda $", "Queda ₽"], filas_lim,
               {"Puedes S/": SOLES, "Gastado S/": SOLES, "Queda S/": SOLES, "Puedes $": DOLARES, "Gastado $": DOLARES,
                "Queda $": DOLARES, "Puedes ₽": RUBLOS, "Gastado ₽": RUBLOS, "Queda ₽": RUBLOS})
        ws.column_dimensions["A"].width = 28

    # ---- Deudas
    ws = wb.create_sheet("Deudas")
    filas = [(d["deuda"], d["tipo"], d["saldo"], d["moneda"]) + _tres(d["saldo_s"]) +
             (d["tasa"], d["cuota"], int(d["dia"]) if d["dia"] else None) for d in deudas]
    filas.append(("TOTAL", "", None, "") + _tres(pasivos) + (None, None, None))
    fin = _tabla(ws, 1, ["Deuda", "Tipo", "Saldo", "Moneda", "S/", "$", "₽", "Tasa anual", "Cuota", "Día de pago"], filas,
                 dict(TRES, **{"Tasa anual": PORCENTAJE, "Saldo": "#,##0.00", "Cuota": "#,##0.00"}))
    if deudas:
        _grafico(ws, "barra", "Cuánto debo a cada uno (S/)", (5, 1, 5, fin - 1), (1, 2, 1, fin - 1), "L2")
        _grafico(ws, "torta", "A quién le debo", (5, 1, 5, fin - 1), (1, 2, 1, fin - 1), "L20")

    # ---- Cuentas
    ws = wb.create_sheet("Cuentas")
    filas = [(c["nombre"], c["valor"], c["moneda"]) + _tres(c["valor_s"]) for c in cuentas]
    filas.append(("TOTAL", None, "") + _tres(activos))
    fin = _tabla(ws, 1, ["Cuenta", "Saldo", "Moneda", "S/", "$", "₽"], filas, dict(TRES, Saldo="#,##0.00"))
    if cuentas:
        _grafico(ws, "torta", "Dónde está mi dinero", (4, 1, 4, fin - 1), (1, 2, 1, fin - 1), "H2")

    # ---- Metas
    ws = wb.create_sheet("Metas")
    filas = [(m["meta"], m["ahorrado"], m["objetivo"], max(m["objetivo"] - m["ahorrado"], 0), m["avance"],
              F.en_dolares(m["ahorrado"]), F.en_dolares(m["objetivo"])) for m in metas]
    fin = _tabla(ws, 1, ["Meta", "Ahorrado S/", "Objetivo S/", "Falta S/", "Avance", "Ahorrado $", "Objetivo $"], filas,
                 {"Ahorrado S/": SOLES, "Objetivo S/": SOLES, "Falta S/": SOLES, "Avance": PORCENTAJE,
                  "Ahorrado $": DOLARES, "Objetivo $": DOLARES})
    if metas:
        _grafico(ws, "barra", "Ahorrado vs objetivo (S/)", (2, 1, 3, fin), (1, 2, 1, fin), "J2")

    # ---- Presupuesto del mes
    ws = wb.create_sheet("Presupuesto")
    filas = []
    for cat, g, tope, usado in F.estado_presupuesto(r_mes.mensuales, plan, 1.0):
        filas.append((cat, tope, round(g, 2), round(max(tope - g, 0), 2), usado))
    fin = _tabla(ws, 1, ["Categoría", "Presupuesto S/", "Gastado S/", "Queda S/", "Usado"], filas,
                 {"Presupuesto S/": SOLES, "Gastado S/": SOLES, "Queda S/": SOLES, "Usado": PORCENTAJE})
    if filas:
        _grafico(ws, "barra", "Presupuesto vs gastado en %s (S/)" % F.MESES[hoy.month - 1], (2, 1, 3, fin), (1, 2, 1, fin),
                 "H2", alto=max(8, len(filas) * 0.7))

    # ---- Por mes
    ws = wb.create_sheet("Por mes")
    por_mes = defaultdict(lambda: defaultdict(float))
    for m in movs:
        por_mes[int(m["fecha"][5:7])][m["tipo"]] += m["monto_s"]
    filas = []
    for k in range(1, hoy.month + 1):
        d = por_mes.get(k, {})
        ing, gas = round(d.get("Ingreso", 0), 2), round(d.get("Gasto", 0), 2)
        filas.append((MESES[k - 1], ing, gas, round(d.get("Ahorro", 0), 2), round(ing - gas, 2)))
    fin = _tabla(ws, 1, ["Mes", "Ingresos S/", "Gastos S/", "Ahorro S/", "Balance S/"], filas,
                 {"Ingresos S/": SOLES, "Gastos S/": SOLES, "Ahorro S/": SOLES, "Balance S/": SOLES})
    _grafico(ws, "columna", "Ingresos vs gastos por mes (S/)", (2, 1, 3, fin), (1, 2, 1, fin), "G2")
    _grafico(ws, "linea", "Balance por mes (S/)", (5, 1, 5, fin), (1, 2, 1, fin), "G20")

    # ---- Categorias
    ws = wb.create_sheet("Categorías")
    anual = sorted(r_anio.por_categoria.items(), key=lambda x: -x[1])
    filas = [(c, round(r_mes.por_categoria.get(c, 0), 2), round(v, 2), C.grupo(c)) for c, v in anual]
    fin = _tabla(ws, 1, ["Categoría", "Este mes S/", "Este año S/", "Grupo"], filas, {"Este mes S/": SOLES, "Este año S/": SOLES})
    if filas:
        _grafico(ws, "barra", "Gastos por categoría en %d (S/)" % hoy.year, (3, 1, 3, fin), (1, 2, 1, fin), "F2",
                 alto=max(8, len(filas) * 0.7))
        _grafico(ws, "torta", "Necesidad vs deseo este año", (2, fin + 3, 2, fin + 5), (1, fin + 4, 1, fin + 5), "F%d" % (len(filas) + 22))
        ws.cell(row=fin + 3, column=1, value="Grupo").font = Font(bold=True)
        ws.cell(row=fin + 3, column=2, value="S/").font = Font(bold=True)
        for k, grupo in enumerate(("Necesidad", "Deseo"), fin + 4):
            ws.cell(row=k, column=1, value=grupo)
            ws.cell(row=k, column=2, value=round(r_anio.necesidades if grupo == "Necesidad" else r_anio.deseos, 2)).number_format = SOLES

    # ---- Movimientos
    ws = wb.create_sheet("Movimientos")
    filas = [(m["fecha"], m["tipo"], m["categoria"], m["descripcion"]) + _tres(m["monto_s"]) + (m["medio"] or "",)
             for m in movs]
    _tabla(ws, 1, ["Fecha", "Tipo", "Categoría", "Descripción", "S/", "$", "₽", "Medio de pago"], filas, TRES)
    ws.freeze_panes = "A2"
    if filas:
        ws.auto_filter.ref = "A1:H%d" % (len(filas) + 1)

    out = BytesIO()
    wb.save(out)
    return out.getvalue()


def nombre_archivo(hoy: Optional[date] = None) -> str:
    return "Finanzas %s.xlsx" % (hoy or F.hoy()).strftime("%Y-%m-%d")
