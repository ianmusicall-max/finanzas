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
        lim = lineas_limite(F.estado_limite(self.notion, self.bases, min(p.hasta, F.hoy())),
                            {"Diario": ("dia", "semana", "mes"), "Semanal": ("semana", "mes"), "Mensual": ("mes",)}[p.tipo])
        if lim:
            l.append("")
            l.append("<b>📏 Día a día</b>")
            l.extend(lim)
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
    for cat, g, tope, usado in F.estado_presupuesto(r.por_categoria, plan, avance):
        if usado is None:
            l.append("⚪ %s: %s <i>(sin presupuesto)</i>" % (esc(cat), F.s(g)))
            continue
        marca = "🔴" if usado >= 1 else "🟡" if usado > avance + 0.1 else "🟢"
        l.append("%s %s\n    %s %s de %s · queda %s" % (marca, esc(cat), barra(usado), F.s(g), F.s(tope), F.s(max(tope - g, 0))))
    total = sum(plan.values())
    l.append("")
    l.append("Total: %s de %s (%s)" % (F.s(r.gastos), F.s(total), F.pct(r.gastos / total if total else None)))
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


NOMBRES_LIMITE = {"dia": "Hoy", "semana": "Semana", "mes": "Mes"}


def lineas_limite(e: Optional[dict], cuales=("dia", "semana", "mes")) -> list:
    """📏 Hoy ₽ 1,200 de ₽ 1,500 … para el limite del dia a dia."""
    if not e:
        return []
    mon = e["moneda"]
    l = []
    for k in cuales:
        x = e[k]
        linea = "%s %s: %s de %s" % (F.marca_limite(x["usado"]), NOMBRES_LIMITE[k], F.en_moneda(x["gastado"], mon), F.en_moneda(x["tope"], mon))
        if x["queda"] < 0:
            linea += " · te pasaste %s" % F.en_moneda(-x["queda"], mon)
        elif k != "dia" and x["dias"] > 1:
            linea += " · quedan %s (%s por día, %d días)" % (F.en_moneda(x["queda"], mon), F.en_moneda(x["por_dia"], mon), x["dias"])
        else:
            linea += " · quedan %s" % F.en_moneda(x["queda"], mon)
        l.append(linea)
    return l


def texto_limite(notion, bases: dict) -> str:
    e = F.estado_limite(notion, bases)
    if not e:
        return ("📏 <b>Límite del día a día</b>\n\nAún no tienes límite. Fíjalo con lo que puedes gastar por día:\n"
                "<code>/limite 1500 rub</code> · <code>/limite 64</code> (soles) · <code>/limite 19 usd</code>\n\n"
                "La semana vale 7 días y el mes, los días que tenga. No cuentan los gastos fijos del mes "
                "(vivienda, universidad, padres, servicios, suscripciones, salud…).")
    return "\n".join(["📏 <b>Límite del día a día</b> · %s por día" % F.en_moneda(e["por_dia"], e["moneda"]), ""]
                     + lineas_limite(e) + ["", "<i>No cuentan los gastos fijos del mes. Cambiarlo: /limite 1500 rub · quitarlo: /limite 0</i>"])


def texto_deudas(notion, bases: dict) -> str:
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
        if d["dia"]:
            det.append("paga el día %d" % int(d["dia"]))
        if det:
            l.append("    " + " · ".join(det))
    l.append("")
    if cuotas:
        l.append("📅 Cuotas al mes: %s" % F.s(cuotas))
    l.append("Para registrar un pago: <code>/pago %s 300</code>" % esc(lista[0]["deuda"].split()[-1]))
    return "\n".join(l)
