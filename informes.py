"""Los resumenes diario, semanal y mensual: el texto que llega por Telegram y la
fila que queda en la base Resumenes de Notion (una por periodo, se reescribe
si se vuelve a calcular)."""
from datetime import date, timedelta
from typing import Optional

import categorias as C
import finanzas as F
from notion import RESUMENES, p_date, p_number, p_select, p_text, p_title
from telegram import esc


def barra(x: Optional[float], ancho: int = 10) -> str:
    if x is None:
        return ""
    llenos = max(0, min(ancho, round(x * ancho)))
    return "▓" * llenos + "░" * (ancho - llenos)


def variacion(ahora: float, antes: float) -> str:
    if antes <= 0:
        return ""
    v = (ahora - antes) / antes
    flecha = "▲" if v > 0 else "▼"
    return " (%s %s vs. anterior)" % (flecha, F.pct(abs(v)))


class Informe:
    """Junta todo lo que hace falta para un periodo y lo presenta."""

    def __init__(self, notion, bases: dict, periodo: F.Periodo, dia_de_corte: Optional[date] = None):
        self.notion, self.bases, self.p = notion, bases, periodo
        corte = dia_de_corte or min(periodo.hasta, F.hoy())
        self.movs = F.movimientos(notion, bases, periodo.desde, periodo.hasta)
        self.r = F.resumir(self.movs, periodo)
        self.prev = None
        if periodo.tipo != "Diario":
            ant = periodo.anterior()
            self.prev = F.resumir(F.movimientos(notion, bases, ant.desde, ant.hasta), ant)
        # el presupuesto es mensual: se mide con lo que va del mes, sea cual sea el periodo
        m = F.mes(corte)
        self.avance_mes = corte.day / m.dias
        if periodo.tipo == "Mensual":
            self.mes = self.r
            self.avance_mes = 1.0 if corte >= periodo.hasta else self.avance_mes
        else:
            self.mes = F.resumir(F.movimientos(notion, bases, m.desde, corte), m)
        self.plan = F.presupuesto(notion, bases)
        self.items = F.patrimonio(notion, bases)
        self.activos, self.pasivos, self.neto, self.liquidez = F.neto(self.items)
        # gasto de un mes normal: el mes pasado; si no hay datos, lo que va de este proyectado
        mp = F.mes(m.desde - timedelta(days=1))
        pasado = F.resumir(F.movimientos(notion, bases, mp.desde, mp.hasta), mp).gastos
        self.gasto_mensual = pasado or (self.mes.gastos / self.avance_mes if self.avance_mes else 0)
        self.consejos = F.consejos(self.mes if periodo.tipo != "Mensual" else self.r, self.plan, self.items,
                                   self.gasto_mensual, self.avance_mes)

    # ---------------------------------------------------------------- texto
    def texto(self) -> str:
        r, p = self.r, self.p
        encabezado = {"Diario": "📅", "Semanal": "🗓", "Mensual": "📆"}[p.tipo]
        l = ["%s <b>%s</b>" % (encabezado, esc(p.titulo))]
        if r.cantidad == 0:
            l.append("Sin movimientos registrados." if p.tipo != "Diario" else "Hoy no registraste movimientos. ¿Seguro que no gastaste nada? 🙂")
        else:
            l.append("")
            l.append("💸 Gastos: <b>%s</b>%s" % (F.s3(r.gastos), variacion(r.gastos, self.prev.gastos) if self.prev else ""))
            if r.ingresos:
                l.append("💰 Ingresos: <b>%s</b>%s" % (F.s3(r.ingresos), variacion(r.ingresos, self.prev.ingresos) if self.prev else ""))
            if r.ahorro:
                l.append("🐷 Ahorro: %s" % F.s(r.ahorro))
            if r.inversion:
                l.append("📈 Inversión: %s" % F.s(r.inversion))
            if r.ingresos:
                l.append("⚖️ Balance: <b>%s</b> · tasa de ahorro %s" % (F.s3(r.balance), F.pct(r.tasa_ahorro)))
            if p.tipo != "Diario" and r.gastos:
                l.append("   necesidades %s · deseos %s" % (F.pct(r.parte("Necesidad")), F.pct(r.parte("Deseo"))))
            if p.tipo == "Diario":
                l.append("")
                for m in self.movs[:15]:
                    signo = "+" if m["tipo"] == "Ingreso" else ""
                    l.append("%s %s%s · %s" % (C.emoji(m["tipo"], m["categoria"]), signo, F.s(m["monto_s"]), esc(m["descripcion"])))
                if len(self.movs) > 15:
                    l.append("… y %d más" % (len(self.movs) - 15))
            elif r.por_categoria:
                l.append("")
                l.append("<b>En qué se fue</b>")
                for cat, v in r.top(6):
                    l.append("%s %s: %s" % (C.emoji("Gasto", cat), esc(cat), F.s(v)))
        if p.tipo != "Diario":
            fuera = F.gastos_fuera(r, self.plan, F.presupuesto_anual(self.notion, self.bases))
            if fuera:
                l.append("")
                l.append("⚠️ <b>Fuera del presupuesto</b>: %s · total %s" % (
                    " · ".join("%s %s" % (esc(c), F.s(v)) for c, v in sorted(fuera.items(), key=lambda x: -x[1])),
                    F.s(sum(fuera.values()))))
        lim = lineas_limite(F.estado_limite(self.notion, self.bases, min(p.hasta, F.hoy())),
                            {"Diario": ("dia", "semana", "mes"), "Semanal": ("semana", "mes"), "Mensual": ("mes",)}[p.tipo])
        if lim:
            l.append("")
            l.append("<b>📏 Día a día</b>")
            l.extend(lim)
        if p.tipo != "Diario" and p.desde <= F.hoy() <= p.hasta:
            pro = lineas_proyeccion(F.proyeccion(self.notion, self.bases, F.hoy()))
            if pro:
                l.append("")
                l.extend(pro)
        if p.tipo == "Diario":
            proximas = F.renovaciones(self.notion, self.bases, min(p.hasta, F.hoy()))
            if proximas:
                l.append("")
                for x in proximas:
                    l.append("🔁 %s se renueva el %s: %s %s" % (esc(x["nombre"]), "/".join(reversed(x["proximo"][5:10].split("-"))),
                                                             x["moneda"], "{:,.2f}".format(x["monto"])))
        if p.tipo != "Mensual" and self.mes.gastos:
            l.append("")
            gastado = self.mes.gastos
            tope = sum(self.plan.values())
            if tope:
                l.append("🧾 En el mes llevas %s de %s presupuestados (%s; el mes va en %s)" % (
                    F.s(gastado), F.s(tope), F.pct(gastado / tope), F.pct(self.avance_mes)))
            else:
                l.append("🧾 En el mes llevas %s gastados." % F.s(gastado))
        if self.items and p.tipo != "Diario":
            l.append("")
            l.append("🏦 Patrimonio neto: <b>%s</b> (activos %s · deudas %s)" % (F.s3(self.neto), F.s(self.activos), F.s(self.pasivos)))
        if self.consejos and (p.tipo != "Diario" or any(c[0] in "🔴🟠" for c in self.consejos)):
            l.append("")
            l.append("<b>Para tener en cuenta</b>")
            lista = self.consejos if p.tipo != "Diario" else [c for c in self.consejos if c[0] in "🔴🟠"]
            for c in lista[:5]:
                l.append(esc(c))
        return "\n".join(l)

    # ---------------------------------------------------------------- notion
    def propiedades(self) -> dict:
        r = self.r
        top = ", ".join("%s %s" % (c, F.s(v)) for c, v in r.top(5))
        return {
            "Periodo": p_title(self.p.clave),
            "Tipo": p_select(self.p.tipo),
            "Fechas": p_date(self.p.desde, self.p.hasta if self.p.hasta != self.p.desde else None),
            "Ingresos S/": p_number(r.ingresos),
            "Gastos S/": p_number(r.gastos),
            "Ahorro S/": p_number(r.ahorro),
            "Inversión S/": p_number(r.inversion),
            "Balance S/": p_number(r.balance),
            "Tasa de ahorro": p_number(round(r.tasa_ahorro, 4) if r.tasa_ahorro is not None else None),
            "Necesidades %": p_number(round(r.parte("Necesidad"), 4) if r.gastos else None),
            "Deseos %": p_number(round(r.parte("Deseo"), 4) if r.gastos else None),
            "Patrimonio neto S/": p_number(self.neto if self.items else None),
            "Principales gastos": p_text(top),
            "Alertas": p_text(" · ".join(self.consejos[:5])),
        }

    def guardar(self) -> dict:
        if RESUMENES not in self.bases:
            return {}
        db = self.bases[RESUMENES]
        ya = self.notion.consultar(db, {"property": "Periodo", "title": {"equals": self.p.clave}}, limite=3)
        if ya:
            return self.notion.editar_pagina(ya[0]["_id"], self.propiedades())
        return self.notion.crear_pagina(db, self.propiedades())


def texto_presupuesto(notion, bases: dict, corte: Optional[date] = None) -> str:
    corte = corte or F.hoy()
    m = F.mes(corte)
    r = F.resumir(F.movimientos(notion, bases, m.desde, corte), m)
    plan = F.presupuesto(notion, bases)
    avance = corte.day / m.dias
    l = ["🧾 <b>Presupuesto de %s</b> · el mes va en %s" % (F.MESES[corte.month - 1], F.pct(avance)), ""]
    if not plan:
        l.append("Todavía no hay presupuesto. Fija uno por categoría:\n<code>/presupuesto comida 800</code>\n<code>/presupuesto transporte 300</code>")
        if r.por_categoria:
            l.append("\nEste mes llevas:")
            for cat, v in r.top(8):
                l.append("%s %s: %s" % (C.emoji("Gasto", cat), esc(cat), F.s(v)))
        return "\n".join(l)
    for cat, g, tope, usado in F.estado_presupuesto(r.mensuales, plan, avance):
        if usado is None:
            if F.fuera_de_presupuesto(cat, plan):
                l.append("⚠️ %s: %s <i>(fuera del presupuesto)</i>" % (esc(cat), F.s(g)))
            else:
                l.append("⚪ %s: %s <i>(día a día, lo controla /limite)</i>" % (esc(cat), F.s(g)))
            continue
        marca = "🔴" if usado >= 1 else "🟡" if usado > avance + 0.1 else "🟢"
        l.append("%s %s\n    %s %s de %s · queda %s" % (marca, esc(cat), barra(usado), F.s(g), F.s(tope), F.s(max(tope - g, 0))))
    total = sum(plan.values())
    mensual = round(sum(r.mensuales.values()), 2)
    l.append("")
    l.append("Total del mes: %s de %s (%s)" % (F.s(mensual), F.s(total), F.pct(mensual / total if total else None)))
    anual = F.presupuesto_anual(notion, bases)
    if anual:
        l.append("")
        l.append("<b>Pagos anuales de %d</b>" % corte.year)
        for cat, tope in sorted(anual.items(), key=lambda x: -x[1]):
            pagado = F.pagado_anual(notion, bases, cat, corte)
            usado = pagado / tope if tope else 0
            marca = "🔴" if usado > 1 else "🟡" if usado >= 0.8 else "🟢"
            l.append("%s %s\n    %s %s de %s · queda %s" % (marca, esc(cat), barra(usado), F.s(pagado), F.s(tope), F.s(max(tope - pagado, 0))))
    return "\n".join(l)


def texto_patrimonio(notion, bases: dict) -> str:
    items = F.patrimonio(notion, bases)
    if not items:
        return ("🏦 <b>Patrimonio</b>\n\nAún no registras cuentas ni deudas. Por ejemplo:\n"
                "<code>/activo Interbank 5200</code>\n<code>/activo Binance 800 usd</code>\n"
                "<code>/activo Auto 45000 vehiculo</code>\n<code>/deuda Tarjeta Falabella 1200</code>")
    act, pas, net, liq = F.neto(items)
    l = ["🏦 <b>Patrimonio neto: %s</b>" % F.s3(net), ""]
    for clase, titulo in (("Activo", "Lo que tienes"), ("Pasivo", "Lo que debes")):
        grupo = [i for i in items if i["clase"] == clase]
        if not grupo:
            continue
        l.append("<b>%s</b> · %s" % (titulo, F.s(act if clase == "Activo" else pas)))
        for i in sorted(grupo, key=lambda i: -i["valor_s"]):
            extra = "" if i["moneda"] == "PEN" else " (%s %s)" % (i["moneda"], "{:,.2f}".format(i["valor"]))
            l.append("  • %s: %s%s <i>%s</i>" % (esc(i["nombre"]), F.s(i["valor_s"]), extra, esc(i["tipo"])))
        l.append("")
    l.append("💧 Disponible (efectivo y bancos): %s" % F.s(liq))
    return "\n".join(l).rstrip()


def texto_metas(notion, bases: dict) -> str:
    lista = F.metas(notion, bases)
    if not lista:
        return ("🎯 <b>Metas</b>\n\nAún no hay metas. Crea una con:\n<code>/meta Fondo de emergencia 20000</code>\n"
                "Y cuando ahorres: <code>ahorro 500 emergencia</code>")
    l = ["🎯 <b>Metas de ahorro</b>", ""]
    for m in lista:
        falta = max(m["objetivo"] - m["ahorrado"], 0)
        l.append("<b>%s</b> %s\n    %s %s · %s de %s · faltan %s" % (
            esc(m["meta"]), "✅" if m["avance"] >= 1 else "", barra(m["avance"]), F.pct(m["avance"]),
            F.s(m["ahorrado"]), F.s(m["objetivo"]), F.s(falta)))
    return "\n".join(l)


def texto_suscripciones(notion, bases: dict) -> str:
    lista = F.suscripciones(notion, bases)
    if not lista:
        return ("🔁 <b>Suscripciones</b>\n\nTodavía no hay. Se agregan solas: cuando anotes el pago de una "
                "(<code>20 usd claude pro</code>), el bot te pregunta cada cuánto se paga.")
    total = sum(x["por_mes_s"] for x in lista)
    tope = F.presupuesto(notion, bases).get(F.CATEGORIA_SUSCRIPCIONES)
    l = ["🔁 <b>Suscripciones</b> · %s al mes en promedio" % F.s3(total)]
    if tope:
        l.append("%s Máximo %s al mes (%s)" % (F.marca_limite(total / tope), F.s(tope), F.pct(total / tope)))
    l.append("")
    for x in lista:
        prox = " · próximo pago %s" % "/".join(reversed(x["proximo"][:10].split("-"))) if x["proximo"] else ""
        l.append("• <b>%s</b>: %s %s, %s%s" % (esc(x["nombre"]), x["moneda"], "{:,.2f}".format(x["monto"]),
                                              F.cada_texto(x["cada"]), prox))
    l.append("")
    l.append("<i>Cancelar una: /suscripcion cancelar Netflix</i>")
    return "\n".join(l)


NOMBRES_LIMITE = {"dia": "Hoy", "semana": "Semana", "mes": "Mes"}


def lineas_limite(e: Optional[dict], cuales=("dia", "semana", "mes")) -> list:
    """El limite del dia a dia en soles, dolares y rublos: gastado, limite, lo que queda y por dia."""
    if not e:
        return []
    tc = F.tipo_de_cambio(e["moneda"])
    l = []
    for k in cuales:
        x = e[k]
        titulo = "%s <b>%s</b>" % (F.marca_limite(x["usado"]), NOMBRES_LIMITE[k])
        if k != "dia" and x["dias"] > 1:
            titulo += " · quedan %d días" % x["dias"]
        l.append(titulo)
        l.append("    Gastado: %s" % F.s3(x["gastado"] * tc))
        l.append("    Límite: %s" % F.s3(x["tope"] * tc))
        if x["queda"] < 0:
            l.append("    Te pasaste: %s" % F.s3(-x["queda"] * tc))
        else:
            l.append("    Queda: %s" % F.s3(x["queda"] * tc))
            if k != "dia" and x["dias"] > 1:
                l.append("    Por día: %s" % F.s3(x["por_dia"] * tc))
    return l


def limite_corto(e: Optional[dict]) -> list:
    """Despues de anotar un gasto: cuanto queda hoy, en la semana y en el mes, en las tres monedas."""
    if not e:
        return []
    tc = F.tipo_de_cambio(e["moneda"])
    l = []
    for k in ("dia", "semana", "mes"):
        x = e[k]
        nombre = {"dia": "hoy", "semana": "en la semana", "mes": "en el mes"}[k]
        if x["queda"] < 0:
            l.append("%s Te pasaste %s: %s" % (F.marca_limite(x["usado"]), nombre, F.s3(-x["queda"] * tc)))
        else:
            l.append("%s Quedan %s: %s" % (F.marca_limite(x["usado"]), nombre, F.s3(x["queda"] * tc)))
    return l


def texto_limite(notion, bases: dict) -> str:
    e = F.estado_limite(notion, bases)
    if not e:
        return ("📏 <b>Límite del día a día</b>\n\nAún no tienes límite. Fíjalo con lo que puedes gastar por día:\n"
                "<code>/limite 1500 rub</code> · <code>/limite 64</code> (soles) · <code>/limite 19 usd</code>\n\n"
                "La semana vale 7 días y el mes, los días que tenga. No cuentan los gastos fijos del mes "
                "(vivienda, universidad, padres, servicios, suscripciones, salud…).")
    return "\n".join(["📏 <b>Límite del día a día</b> · %s por día" % F.s3(e["por_dia"] * F.tipo_de_cambio(e["moneda"])), ""]
                     + lineas_limite(e) + ["", "<i>No cuentan los gastos fijos del mes. Cambiarlo: /limite 1500 rub · quitarlo: /limite 0</i>"])


def texto_deudas(notion, bases: dict) -> str:
    compras = F.compras_en_cuotas(notion, bases)
    lista = F.deudas(notion, bases)
    if not lista:
        return ("💳 <b>Deudas</b>\n\nNo tienes deudas activas. 🎉\nSi tienes una, anótala con:\n"
                "<code>/deuda Tarjeta Falabella 1200</code>\n<code>/deuda Préstamo BCP 15000</code>")
    total = sum(d["saldo_s"] for d in lista)
    cuotas = sum(F.soles(d["cuota"], d["moneda"]) for d in lista if d["cuota"])
    l = ["💳 <b>Deudas: %s</b>" % F.s3(total), ""]
    for d in lista:
        extra = "" if d["moneda"] in ("PEN", "USD", "RUB") else " (%s %s)" % (d["moneda"], "{:,.2f}".format(d["saldo"]))
        l.append("<b>%s</b> · %s%s <i>%s</i>" % (esc(d["deuda"]), F.s3(d["saldo_s"]), extra, esc(d["tipo"])))
        det = []
        if d["original"]:
            pagado = 1 - d["saldo"] / d["original"] if d["original"] > 0 else 0
            if pagado > 0:
                det.append("%s %s pagado" % (barra(pagado), F.pct(pagado)))
        if d["tasa"]:
            det.append("tasa %s" % F.pct(d["tasa"]))
        if d["cuota"]:
            det.append("cuota %s" % F.s(F.soles(d["cuota"], d["moneda"])))
        if d.get("corte"):
            det.append("cierra el día %d" % int(d["corte"]))
        if d["dia"]:
            det.append("paga el día %d" % int(d["dia"]))
        if det:
            l.append("    " + " · ".join(det))
        for c in [x for x in compras if C.normal(x["deuda"]) == C.normal(d["deuda"])][:5]:
            l.append("    🧾 %s · %s · %s al mes" % (
                esc(c["descripcion"]),
                "%d cuotas desde %s" % (c["cuotas"], F.mes_texto(c["primera"])) if c["toca"] == 0
                else "cuota %d de %d" % (c["toca"], c["cuotas"]), F.s(c["cuota_s"])))
    l.append("")
    if cuotas:
        l.append("📅 Cuotas al mes: %s" % F.s(cuotas))
    sin_corte = [d for d in lista if d["tipo"] == "Tarjeta de crédito" and not d.get("corte")]
    if sin_corte:
        l.append("<i>🗓 Para saber en qué estado de cuenta cae lo que compras, dime cuándo cierra: "
                 "<code>/corte %s 10</code></i>" % esc(sin_corte[0]["deuda"].split()[-1]))
    l.append("Para registrar un pago: <code>/pago %s 300</code>" % esc(lista[0]["deuda"].split()[-1]))
    return "\n".join(l)


def texto_comparar(notion, bases: dict, d=None, tope: int = 8) -> str:
    """📊 Este mes contra el pasado: los totales y en qué categorías cambió."""
    c = F.comparar_meses(notion, bases, d)
    a, b = c["a"], c["b"]
    mes_a, mes_b = c["este"].titulo.split()[0], c["pasado"].titulo.split()[0]
    l = ["📊 <b>%s contra %s</b>" % (esc(mes_a), esc(mes_b.lower()))]
    if not c["completo"]:
        l.append("<i>Los dos hasta el día %d, para que se puedan comparar.</i>" % c["dia"])
    l.append("")
    if not a.cantidad and not b.cantidad:
        return "\n".join(l + ["Todavía no hay movimientos para comparar."])
    for emoji, nombre, x, y in (("💸", "Gastos", a.gastos, b.gastos), ("💰", "Ingresos", a.ingresos, b.ingresos),
                                ("🐷", "Ahorro", a.ahorro, b.ahorro), ("📈", "Inversión", a.inversion, b.inversion)):
        if x or y:
            l.append("%s %s: <b>%s</b>%s" % (emoji, nombre, F.s(x), variacion(x, y)))
    if a.ingresos or b.ingresos:
        l.append("⚖️ Balance: <b>%s</b>%s" % (F.s(a.balance), variacion(a.balance, b.balance)))
    suben = [x for x in c["cambios"] if abs(x["dif"]) >= 1][:tope]
    if suben:
        l += ["", "<b>En qué cambió</b>"]
        for x in suben:
            if not x["antes"]:
                detalle = "nuevo este mes"
            elif not x["ahora"]:
                detalle = "antes %s, este mes nada" % F.s(x["antes"])
            else:
                detalle = "%s %s · antes %s" % ("↑" if x["dif"] > 0 else "↓", F.pct(abs(x["pct"])), F.s(x["antes"]))
            l.append("%s %s · <b>%s</b> <i>%s</i>" % (C.emoji("Gasto", x["categoria"]), esc(x["categoria"]),
                                                      F.s(x["ahora"]), detalle))
    peor = next((x for x in suben if x["dif"] > 0 and x["antes"]), None)
    if peor:
        l += ["", "<i>Lo que más subió es %s: %s más que el mes pasado.</i>" % (
            esc(peor["categoria"].lower()), F.s(peor["dif"]))]
    return "\n".join(l)


def texto_buscar(notion, bases: dict, texto: str, desde, hasta, cuando: str = "", tope: int = 15) -> str:
    """Lo que encontro /buscar: el total y la lista, del mas nuevo al mas viejo."""
    filas = F.buscar(notion, bases, texto, desde, hasta)
    titulo = "🔍 <b>%s</b>%s" % (esc(texto), " · " + cuando if cuando else "")
    if not filas:
        return "%s\n\nNo encontré nada. Prueba con una palabra sola, o mira /ultimos." % titulo
    gastos = [f for f in filas if f["tipo"] == "Gasto"]
    otros = [f for f in filas if f["tipo"] != "Gasto"]
    l = [titulo, ""]
    if gastos:
        total = sum(f["monto_s"] for f in gastos)
        l.append("<b>%s</b> en %d gasto%s%s" % (F.s3(total), len(gastos), "" if len(gastos) == 1 else "s",
                                                " · %s cada uno" % F.s(total / len(gastos)) if len(gastos) > 1 else ""))
    for tipo in ("Ingreso", "Ahorro", "Inversión"):
        suyos = [f for f in otros if f["tipo"] == tipo]
        if suyos:
            l.append("%s en %d de %s" % (F.s(sum(f["monto_s"] for f in suyos)), len(suyos), tipo.lower()))
    l.append("")
    for f in filas[:tope]:
        monto = F.s(f["monto_s"]) if f["moneda"] == "PEN" else "%s (%s %s)" % (
            F.s(f["monto_s"]), f["moneda"], "{:,.2f}".format(f["monto"]))
        l.append("%s %s%s · %s <i>%s</i>" % (C.emoji(f["tipo"], f["categoria"]),
                                             "+" if f["tipo"] == "Ingreso" else "", monto,
                                             esc(f["descripcion"]), "/".join(reversed(f["fecha"][5:].split("-")))))
    if len(filas) > tope:
        l.append("")
        l.append("<i>Y %d más. Agrega otra palabra para buscar más fino.</i>" % (len(filas) - tope))
    return "\n".join(l)


# ---------------------------------------------------------------- pagos del mes (recordatorios)

def fecha_corta(dia: Optional[int], d: date) -> str:
    return "día %d" % F.dia_del_mes(dia, d) if dia else "sin día"


def monto_rec(r: dict) -> str:
    return "" if not r["monto"] else " · %s" % F.en_moneda(r["monto"], r["moneda"])


def texto_pagos(notion, bases: dict, d: Optional[date] = None) -> str:
    d = d or F.hoy()
    todos = F.recordatorios(notion, bases)
    if not todos:
        return "🔔 <b>Pagos del mes</b>\n\nTodavía no hay recordatorios."
    l = ["🔔 <b>Pagos y recordatorios de %s</b>" % F.MESES[d.month - 1], ""]
    for r in todos:
        hecho = F.hecho_este_mes(r, d)
        marca = "✅" if hecho else ("⏰" if r["dia"] and F.dia_del_mes(r["dia"], d) < d.day else "▫️")
        l.append("%s %s · %s%s" % (marca, esc(r["nombre"]), fecha_corta(r["dia"], d), monto_rec(r)))
    pend = [r for r in todos if not F.hecho_este_mes(r, d)]
    if pend:
        total = sum(F.soles(r["monto"], r["moneda"]) for r in pend if r["monto"] and r["tipo"] in ("Pago", "Deuda"))
        if total:
            l.append("")
            l.append("Falta pagar este mes: %s" % F.s3(total))
    l.append("")
    l.append("<i>⏰ = ya pasó la fecha y no está marcado. Toca un botón cuando lo hagas.</i>")
    return "\n".join(l)


def texto_aviso(r: dict) -> str:
    verbo = {"Retiro": "🏧", "Deuda": "💳", "Pago": "🔔"}.get(r["tipo"], "🔔")
    return "%s <b>Hoy toca: %s</b>%s" % (verbo, esc(r["nombre"]), monto_rec(r))


# ---------------------------------------------------------------- proyeccion del mes

def lineas_proyeccion(p: Optional[dict]) -> list:
    if not p:
        return []
    marca = "🟢" if p["cierre"] >= 0 else "🔴"
    l = ["%s <b>Si no entra más dinero, cierras el mes con %s</b>" % (marca, F.s3(p["cierre"]))]
    l.append("    Entró %s · gastaste %s · ahorraste %s" % (F.s(p["ingresos"]), F.s(p["gastos"]), F.s(p["ahorro"])))
    if p["fijos"]:
        l.append("    Faltan pagos fijos: %s" % F.s(p["fijos"]))
    if p["dias"]:
        l.append("    Día a día de los %d días que quedan: %s" % (p["dias"], F.s(p["dia_a_dia"])))
    return l


def texto_proyeccion(notion, bases: dict) -> str:
    p = F.proyeccion(notion, bases)
    if not p:
        return "📈 <b>Proyección del mes</b>\n\nTodavía no hay movimientos este mes."
    return "\n".join(["📈 <b>Proyección de %s</b>" % F.MESES[F.hoy().month - 1], ""] + lineas_proyeccion(p))


# ---------------------------------------------------------------- plan para salir de deudas

def _cuando(meses: Optional[int]) -> str:
    if meses is None:
        return "no termina (alguna deuda no tiene cuota)"
    fin = F.sumar_meses(F.hoy().replace(day=1), meses)
    return "%s %d (%d meses)" % (F.MESES[fin.month - 1].lower(), fin.year, meses)


def texto_plan(notion, bases: dict, extra_s: Optional[float] = None, extra_txt: str = "") -> str:
    lista = F.deudas(notion, bases)
    if not lista:
        return "🎉 No tienes deudas activas."
    total = sum(d["saldo_s"] for d in lista)
    base = F.plan_deudas(lista, 0)
    l = ["📉 <b>Plan para salir de deudas</b> · debes %s" % F.s3(total), ""]
    l.append("Solo con las cuotas (%s al mes): <b>%s</b>" % (F.s(base["por_mes"]), _cuando(base["meses"])))
    if base["sin_pagar"]:
        l.append("<i>Sin cuota: %s. Ponles una en Notion o págalas con el extra.</i>" % esc(", ".join(base["sin_pagar"])))
    extras = [(extra_s, extra_txt)] if extra_s else [(F.soles(x, "USD"), "$%d" % x) for x in (200, 500)]
    for e, txt in extras:
        p = F.plan_deudas(lista, e)
        l.append("Con %s extra al mes: <b>%s</b>" % (txt or F.s(e), _cuando(p["meses"])))
    con = F.plan_deudas(lista, extras[-1][0])
    l.append("")
    l.append("<b>Orden para el dinero extra</b> (%s):" % ("la de más interés primero" if any(d["tasa"] for d in lista)
                                                         else "la más chica primero: bola de nieve"))
    for k, nombre in enumerate(con["orden"], 1):
        mes_fin = con["fin"].get(nombre)
        l.append("%d. %s%s" % (k, esc(nombre), " · terminas en %s" % _cuando(mes_fin).split(" (")[0] if mes_fin else ""))
    if con["intereses"]:
        l.append("")
        l.append("Intereses que pagarías en el camino: ≈ %s" % F.s(con["intereses"]))
    l.append("")
    l.append("<i>Prueba con otro monto: /plan 300 usd · /plan 1000</i>")
    return "\n".join(l)


# ---------------------------------------------------------------- ingresos por fuente

def texto_ingresos(notion, bases: dict, meses: int = 6) -> str:
    hoy = F.hoy()
    ini = F.sumar_meses(hoy.replace(day=1), -(meses - 1))
    movs = [m for m in F.movimientos(notion, bases, ini, hoy) if m["tipo"] == "Ingreso"]
    if not movs:
        return "💰 <b>Ingresos por fuente</b>\n\nTodavía no hay ingresos anotados."
    claves = [F.sumar_meses(ini, k).isoformat()[:7] for k in range(meses)]
    por = {}
    for m in movs:
        por.setdefault(m["categoria"], {}).setdefault(m["fecha"][:7], 0)
        por[m["categoria"]][m["fecha"][:7]] += m["monto_s"]
    este, antes = claves[-1], claves[-2] if len(claves) > 1 else None
    l = ["💰 <b>Ingresos por fuente</b> · últimos %d meses" % meses, ""]
    for cat, vals in sorted(por.items(), key=lambda x: -sum(x[1].values())):
        tot = sum(vals.values())
        ahora, previo = vals.get(este, 0), vals.get(antes, 0) if antes else 0
        flecha = "" if not previo else (" ↑" if ahora > previo else " ↓" if ahora < previo else " =")
        l.append("%s <b>%s</b>: %s en total" % (C.emoji("Ingreso", cat), esc(cat), F.s3(tot)))
        l.append("    este mes %s · mes pasado %s%s" % (F.s(ahora), F.s(previo), flecha))
    l.append("")
    l.append("<b>Por mes</b>")
    for k in claves:
        v = sum(vals.get(k, 0) for vals in por.values())
        l.append("%s %d: %s" % (F.MESES[int(k[5:7]) - 1][:3], int(k[:4]), F.s3(v)))
    return "\n".join(l)


# ---------------------------------------------------------------- grafico de la semana (imagen)

def url_grafico_semana(notion, bases: dict, d: Optional[date] = None) -> Optional[str]:
    """Imagen de barras de los gastos de la semana por categoria, hecha por quickchart.io (gratis, sin clave)."""
    import json
    from urllib.parse import quote
    d = d or F.hoy()
    sem = F.semana(d)
    r = F.resumir(F.movimientos(notion, bases, sem.desde, min(sem.hasta, d)), sem)
    top = r.top(8)
    if not top:
        return None
    titulo = "Gastos %s - %s: S/ %s" % (sem.desde.strftime("%d/%m"), sem.hasta.strftime("%d/%m"), "{:,.0f}".format(r.gastos))
    lim = F.estado_limite(notion, bases, min(sem.hasta, d))
    if lim:
        tc = F.tipo_de_cambio(lim["moneda"])
        titulo += " | dia a dia S/ %s de S/ %s" % ("{:,.0f}".format(lim["semana"]["gastado"] * tc), "{:,.0f}".format(lim["semana"]["tope"] * tc))
    cfg = {"type": "horizontalBar",
           "data": {"labels": [c for c, _ in top], "datasets": [{"label": "S/", "data": [round(v, 2) for _, v in top],
                                                                  "backgroundColor": "#2F5597"}]},
           "options": {"title": {"display": True, "text": titulo}, "legend": {"display": False}}}
    return "https://quickchart.io/chart?w=700&h=420&bkg=white&c=" + quote(json.dumps(cfg, ensure_ascii=False, separators=(",", ":")))
