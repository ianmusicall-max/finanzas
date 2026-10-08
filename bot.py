#!/usr/bin/env python3
"""Bot de Telegram de finanzas personales: anotas un gasto en un mensaje
("45 almuerzo") y queda en Notion. Tambien muestra resumenes, presupuesto,
patrimonio y metas.

Uso:
    python3 bot.py            # corre hasta que lo detengas (Ctrl+C)
    python3 bot.py --una-vez  # procesa lo pendiente y sale (para probar)
"""
import argparse
import re
import sys
import time
from typing import Optional
from datetime import timedelta

import categorias as C
import excel as X
import finanzas as F
import informes as I
from config import DATA, TELEGRAM_USUARIOS
from notion import DEUDAS, METAS, MOVIMIENTOS, PATRIMONIO, PRESUPUESTO, SUSCRIPCIONES, Notion, NotionError, cargar_bases, p_select
from formularios import Formularios
from lector import MONEDAS, Movimiento, NoEntendi, _numero, interpretar
from telegram import Telegram, TelegramError, esc, guardar_offset, leer_offset, turno_del_bot

AYUDA = (
    "💰 <b>Finanzas</b> · todo queda en Notion\n\n"
    "<b>Anotar</b> (con botones):\n"
    "<code>300 sofá falabella 6 cuotas</code> · compra a crédito en cuotas\n"
    "/gasto · /ingreso · /ahorro · /inversion\n\n"
    "<b>Ver</b>\n"
    "/hoy · /ayer · /semana · /mes · resúmenes\n"
    "/presupuesto · cuánto llevas de cada categoría\n"
    "/patrimonio · lo que tienes menos lo que debes\n"
    "/metas · avance de tus metas de ahorro\n"
    "/deudas · cuánto debes y a quién\n"
    "/excel · todo en un Excel con gráficos\n"
    "/limite · cuánto llevas gastado hoy, en la semana y en el mes\n"
    "/suscripciones · tus suscripciones y cuándo se renuevan\n"
    "/pagos · pagos y recordatorios del mes (servicios, bancos, retiros)\n"
    "/retirar · sacaste efectivo de un banco: baja la cuenta y sube tu efectivo (no es gasto)\n"
    "/proyeccion · cómo cierras el mes si no entra más dinero\n"
    "/plan · cuándo terminas de pagar tus deudas (y con extra: /plan 300 usd)\n"
    "/ingresos · cuánto deja cada fuente, mes a mes\n"
    "/grafico · imagen con los gastos de la semana\n"
    "/consejos · qué mejorar según tus números\n"
    "/metodos · formas de manejar tu dinero\n"
    "/ultimos · lo último que anotaste, con botones para corregir el monto o borrar\n"
    "<code>/buscar farmacia</code> · busca en todo tu historial (<code>/buscar uber mes</code>)\n\n"
    "<b>Ajustar</b>\n"
    "<code>/presupuesto comida 800</code>\n"
    "<code>/activo Interbank 5200</code> · <code>/deuda Tarjeta Falabella 1200</code>\n"
    "<code>/pago Falabella 300</code> · baja el saldo de una deuda\n"
    "<code>/meta Auto 100000</code>\n"
    "<code>/tc 3.72</code> · <code>/tc rub 0.046</code> · tipo de cambio\n"
    "/deshacer · borra lo último que anotaste (para uno viejo, /ultimos)"
)

MENU = [[("➖ Gasto", "m:gasto"), ("➕ Ingreso", "m:ingreso"), ("🐷 Ahorro", "m:ahorro")],
        [("🏧 Retirar efectivo", "m:retirar")],
        [("📅 Hoy", "m:hoy"), ("🗓 Semana", "m:semana"), ("📆 Mes", "m:mes")],
        [("📏 Límite", "m:limite"), ("🧾 Presupuesto", "m:presupuesto"), ("💳 Deudas", "m:deudas")],
        [("🏦 Patrimonio", "m:patrimonio"), ("🎯 Metas", "m:metas"), ("🔁 Suscripciones", "m:suscripciones")],
        [("🔔 Pagos del mes", "m:pagos"), ("📈 Proyección", "m:proyeccion"), ("📉 Plan deudas", "m:plan")],
        [("💰 Ingresos", "m:ingresos"), ("📊 Excel", "m:excel"), ("🖼 Gráfico", "m:grafico")],
        [("💡 Consejos", "m:consejos"), ("💱 Tipo de cambio", "m:tc"), ("⚙️ Ajustar", "m:ajustar")]]

MENU_VER = [[("📏 Límite", "m:limite"), ("🧾 Presupuesto", "m:presupuesto")],
            [("💳 Deudas", "m:deudas"), ("🏦 Patrimonio", "m:patrimonio")],
            [("🎯 Metas", "m:metas"), ("🔁 Suscripciones", "m:suscripciones")],
            [("📊 Excel", "m:excel"), ("💡 Consejos", "m:consejos")],
            [("🧾 Últimos", "m:ultimos"), ("💱 Tipo de cambio", "m:tc")]]

# Ajustar: cada boton pide un dato y lo que se escribe despues va a ese comando.
AJUSTES_BOT = {
    "limite": ("📏 Límite diario", "/limite", "📏 ¿Cuánto puedes gastar por día en el día a día?\nEscribe el monto y la moneda, por ejemplo: <code>1500 rub</code> · <code>64</code> (soles) · <code>19 usd</code>"),
    "presupuesto": ("🧾 Presupuesto", "/presupuesto", "🧾 Escribe la categoría y el tope.\nAl mes: <code>supermercado 855</code> · Pagos de una vez al año: <code>suscripciones anual 600</code>"),
    "cuenta": ("🏦 Saldo de una cuenta", "/activo", "🏦 Escribe la cuenta y cuánto tiene hoy, por ejemplo: <code>T-Bank 25000 rub</code> · <code>Interbank dólares 1497 usd</code>"),
    "deuda": ("💳 Deuda nueva o saldo", "/deuda", "💳 Escribe la deuda y cuánto debes hoy, por ejemplo: <code>Tarjeta BBVA 1200</code> · <code>Juan 200 usd</code>"),
    "meta": ("🎯 Meta de ahorro", "/meta", "🎯 Escribe la meta y el objetivo en soles, por ejemplo: <code>Viaje a Cusco 5000</code>"),
    "tc": ("💱 Tipo de cambio", "/tc", "💱 Escribe el tipo de cambio: <code>3.38</code> (dólar) · <code>rub 0.0428</code> · o <code>auto</code> para el del día"),
}
MENU_AJUSTAR = [[(AJUSTES_BOT["limite"][0], "aj:limite"), (AJUSTES_BOT["presupuesto"][0], "aj:presupuesto")],
                [(AJUSTES_BOT["cuenta"][0], "aj:cuenta"), (AJUSTES_BOT["deuda"][0], "aj:deuda")],
                [("💸 Pagar una deuda", "m:pago"), (AJUSTES_BOT["meta"][0], "aj:meta")],
                [(AJUSTES_BOT["tc"][0], "aj:tc"), ("↩️ Deshacer lo último", "m:deshacer")]]

METODOS = (
    "🧭 <b>Formas de manejar tu dinero</b>\n\n"
    "<b>1. 50/30/20</b> (la más simple)\n"
    "50% necesidades, 30% deseos, 20% ahorro e inversión. El bot ya separa tus gastos en necesidades y deseos "
    "y te dice en cada resumen cómo vas.\n\n"
    "<b>2. Págate primero</b>\n"
    "El día que cobras separas el ahorro (<code>ahorro 700 emergencia</code>) y vives con el resto. "
    "Funciona mejor que ahorrar \"lo que sobre\", porque casi nunca sobra.\n\n"
    "<b>3. Sobres (presupuesto por categoría)</b>\n"
    "Cada categoría tiene un tope mensual (<code>/presupuesto comida 800</code>). Cuando se acaba el sobre, se acabó. "
    "El bot te avisa al 80% y al 100%.\n\n"
    "<b>4. Presupuesto base cero</b>\n"
    "Cada sol de tus ingresos tiene destino antes de empezar el mes: ingresos − gastos − ahorro − inversión = 0. "
    "Es el más exigente y el que más control da; útil si tus ingresos varían (Facebook, distribuidoras).\n\n"
    "<b>5. Deudas: avalancha o bola de nieve</b>\n"
    "Avalancha: pagas primero la deuda con mayor interés (las tarjetas); ahorra más dinero. "
    "Bola de nieve: pagas primero la más chica; da motivación rápida.\n\n"
    "<b>Orden recomendado</b>\n"
    "① Anotar todo un mes sin juzgar → ② fondo de emergencia de 3 a 6 meses de gastos → "
    "③ cero deudas de tarjeta → ④ metas (auto, depa) → ⑤ invertir lo que sobra.\n\n"
    "Con ingresos en dólares (Facebook, Payoneer), conviene guardar el fondo de emergencia en soles "
    "y decidir aparte cuánto mantener en dólares."
)


def codigo_salida(exc) -> int:
    """401: el token no sirve -> 2. 409: otro lector del mismo bot -> 3. Cualquier otro -> 1.
    systemd no reinicia 2 ni 3 (RestartPreventExitStatus): quedan visibles en rojo."""
    code = getattr(exc, "code", None)
    if code == 401:
        print("  [telegram] el token no sirve (401). Revisa TELEGRAM_TOKEN en el .env.")
        return 2
    if code == 409:
        print("  [telegram] otro proceso o un webhook ya lee este bot (409). Apaga la otra copia.")
        return 3
    print("  [telegram] %s" % exc)
    return 1


def _pid(page_id: str) -> str:
    return (page_id or "").replace("-", "")


# ---------------------------------------------------------------- patrimonio

TIPOS_ACTIVO = [
    ("Cripto", ["cripto", "binance", "usdt", "btc", "bitcoin", "eth"]),
    ("Inversiones", ["inversion", "fondo", "acciones", "etf", "bolsa", "plazo fijo", "afp"]),
    ("Inmueble", ["inmueble", "casa", "depa", "departamento", "terreno", "local"]),
    ("Vehículo", ["vehiculo", "auto", "carro", "moto", "camioneta"]),
    ("Por cobrar", ["cobrar", "me deben", "prestamo a"]),
    ("Efectivo y bancos", ["banco", "efectivo", "cuenta", "ahorros", "interbank", "bcp", "bbva", "sip", "yape", "paypal", "payoneer"]),
]
TIPOS_DEUDA = [
    ("Tarjeta de crédito", ["tarjeta", "falabella", "cmr", "oh", "visa", "mastercard", "amex"]),
    ("Hipoteca", ["hipoteca", "hipotecario"]),
    ("Préstamo", ["prestamo", "credito", "banco"]),
    ("Persona", ["amigo", "amiga", "mama", "papa", "hermano", "hermana", "tio", "tia", "primo", "prima"]),
]


def _tipo_patrimonio(clase: str, texto: str) -> str:
    t = " %s " % C.normal(texto)
    for tipo, claves in (TIPOS_ACTIVO if clase == "Activo" else TIPOS_DEUDA):
        if any(" %s " % k in t or (len(k) > 4 and k in t) for k in claves):
            return tipo
    return "Efectivo y bancos" if clase == "Activo" else "Otra"


def leer_patrimonio(clase: str, texto: str):
    """'Binance 800 usd' -> (nombre, valor, moneda, tipo)"""
    m = re.search(r"(?<![\w])(\d[\d.,]*)(\s*k)?(?![\w])", texto)
    if not m:
        raise NoEntendi("Falta el monto. Ejemplo: /activo Interbank 5200")
    valor = _numero(m.group(1)) * (1000 if m.group(2) else 1)
    nombre = texto[:m.start()].strip(" :-")
    resto = texto[m.end():].split()
    moneda = "PEN"
    extra = []
    for w in resto:
        wn = C.normal(w)
        if wn in MONEDAS:
            moneda = MONEDAS[wn]
        else:
            extra.append(w)
    if not nombre:
        nombre = " ".join(extra).strip()
        extra = []
    if not nombre:
        raise NoEntendi("Falta el nombre. Ejemplo: /activo Interbank 5200")
    return nombre[:1].upper() + nombre[1:], valor, moneda, _tipo_patrimonio(clase, nombre + " " + " ".join(extra))


def _monto_y_moneda(texto: str) -> tuple:
    """'45' -> (45.0, None) · '20 usd' -> (20.0, 'USD'). Sin monto valido levanta ValueError."""
    moneda, numero = None, None
    for w in texto.replace("S/", " ").split():
        wn = C.normal(w).strip(".,")
        if wn in MONEDAS:
            moneda = MONEDAS[wn]
            continue
        try:
            numero = _numero(w.lstrip("$€₽").strip())
        except ValueError:
            continue
    if numero is None or numero <= 0:
        raise ValueError(texto)
    return round(numero, 2), moneda


# ---------------------------------------------------------------- bot

class Bot:
    def __init__(self, tg, notion, bases: dict, usuarios: set):
        self.tg = tg
        self.notion = notion
        self.bases = bases
        self.usuarios = usuarios
        self._avisados = set()     # chats desconocidos a los que ya se les dijo que no
        self._ultimo = {}          # chat -> page_id del ultimo movimiento anotado
        self._metas_de = {}        # page_id de un ahorro -> (meta_id, monto) para poder deshacer
        self._credito_de = {}      # page_id de un gasto a credito -> (deuda_id, cargo) para poder deshacer
        self._cuenta_de = {}       # page_id de un movimiento -> (cuenta_id, delta) para poder deshacer
        self._por_ahorrar = {}     # chat -> ingreso recien anotado, mientras se elige cuanto separar
        self._pagando = {}         # chat -> pago de deuda en curso (con botones)
        self._suscribiendo = {}    # chat -> pago de una suscripcion nueva, mientras se elige cada cuanto se paga
        self._ajustando = {}       # chat -> comando que espera el dato que se escriba (botones de Ajustar)
        self._retirando = {}       # chat -> retiro de efectivo en curso (cuenta elegida, esperando el monto)
        self._retiro_de = {}       # chat -> ultimo retiro (banco_id, efectivo_id, monto) para poder deshacer
        self._corrigiendo = {}     # chat -> page_id del movimiento al que le esta cambiando el monto
        self.form = Formularios(metas=self._nombres_metas, anuales=self._categorias_anuales)

    def _categorias_anuales(self) -> set:
        try:
            return set(F.presupuesto_anual(self.notion, self.bases))
        except NotionError:
            return set()

    def _nombres_metas(self) -> list:
        if METAS not in self.bases:
            return []
        try:
            return [m["meta"] for m in F.metas(self.notion, self.bases)]
        except NotionError:
            return []

    def _responder(self, chat, respuestas: list) -> None:
        for r in respuestas:
            self.decir(chat, r["texto"], r.get("botones"))

    # ---- envio
    def decir(self, chat, texto: str, botones=None) -> None:
        try:
            self.tg.enviar(chat, texto, botones)
        except TelegramError as exc:
            print("  [telegram] no pude enviar: %s" % exc)

    # ---- entrada
    def procesar(self, update: dict) -> None:
        msg = update.get("message")
        cb = update.get("callback_query")
        if cb:
            m = cb.get("message") or {}
            chat = (m.get("chat") or {}).get("id")
            self.tg.responder_callback(cb["id"])
            if chat is None or (m.get("chat") or {}).get("type", "private") != "private":
                return   # el bot solo atiende en chats privados
            if not self._autorizado(chat, (cb.get("from") or {}).get("id")):
                return
            self._boton(chat, m.get("message_id"), cb.get("data") or "")
            return
        if not msg or "text" not in msg:
            return
        if (msg.get("chat") or {}).get("type", "private") != "private":
            return
        chat = msg["chat"]["id"]
        if not self._autorizado(chat, (msg.get("from") or {}).get("id")):
            return
        texto = msg["text"].strip()
        try:
            if texto.startswith("/"):
                self._ajustando.pop(chat, None)
                self._comando(chat, texto)
            elif chat in self._ajustando:
                self._comando(chat, self._ajustando.pop(chat) + " " + texto)
            elif (self._por_ahorrar.get(chat) or {}).get("esperando"):
                self._monto_a_ahorrar(chat, texto)
            elif (self._pagando.get(chat) or {}).get("esperando"):
                self._monto_pagado(chat, texto)
            elif (self._retirando.get(chat) or {}).get("esperando"):
                self._monto_retiro(chat, texto)
            elif (self._suscribiendo.get(chat) or {}).get("esperando"):
                self._meses_suscripcion(chat, texto)
            elif chat in self._corrigiendo:
                self._cambiar_monto(chat, texto)
            elif self.form.activo(chat):
                self._responder(chat, self.form.texto(chat, texto))
            else:
                self._anotar(chat, texto)
        except NotionError as exc:
            self.decir(chat, "⚠️ Notion no respondió, no se guardó nada. Intenta de nuevo en un rato.\n<i>%s</i>" % esc(str(exc)[:200]))

    def _autorizado(self, chat, user) -> bool:
        if user in self.usuarios:
            return True
        if chat in self._avisados:
            return False
        self._avisados.add(chat)
        if not self.usuarios:
            self.decir(chat, "Este bot no tiene usuarios autorizados. Tu ID es <code>%s</code>: "
                             "pégalo en TELEGRAM_USUARIOS del .env y reinicia el bot." % esc(user))
        else:
            self.decir(chat, "No estás autorizado. Tu ID es <code>%s</code>." % esc(user))
        return False

    # ---- anotar
    def _anotar(self, chat, texto: str, tipo=None) -> None:
        try:
            mov = interpretar(texto, tipo)
        except NoEntendi as exc:
            self.decir(chat, "🤔 %s\n\nUsa el formulario o escribe por ejemplo <code>45 almuerzo</code>." % esc(exc), MENU)
            return
        self._guardar(chat, mov, mov.descripcion if mov.tipo == "Ahorro" else None)

    def _guardar(self, chat, mov, nombre_meta=None) -> None:
        """Guarda en Notion y contesta con el resumen y los botones de corregir o deshacer."""
        meta = None
        if mov.tipo == "Ahorro" and nombre_meta and METAS in self.bases:
            meta = F.buscar_meta(F.metas(self.notion, self.bases), nombre_meta)
            if meta:
                mov.categoria = "Fondo de emergencia" if "emergencia" in C.normal(meta["meta"]) else "Metas"
                mov.adivinada = True
        sus, nueva_sus = None, False
        if mov.tipo == "Gasto" and mov.categoria == F.CATEGORIA_SUSCRIPCIONES and SUSCRIPCIONES in self.bases:
            sus = F.buscar_suscripcion(F.suscripciones(self.notion, self.bases), mov.descripcion)
            if sus:
                mov.frecuencia = "Anual" if sus["cada"] > 1 else None
            else:
                nueva_sus = True
        pag = F.guardar_movimiento(self.notion, self.bases, mov)
        pid = _pid(pag["id"])
        self._ultimo[chat] = pid
        if sus:
            r = F.registrar_pago_suscripcion(self.notion, self.bases, sus["nombre"], mov.monto, mov.moneda, sus["cada"], mov.fecha, sus)
        l = ["%s <b>%s</b> · %s" % (C.emoji(mov.tipo, mov.categoria), esc(mov.tipo), esc(mov.categoria))]
        monto = F.s3(F.soles(mov.monto, mov.moneda))
        if mov.moneda != "PEN":
            monto = "%s %s = %s\n<i>💱 1 %s = S/ %s</i>" % (mov.moneda, "{:,.2f}".format(mov.monto), monto,
                                                          mov.moneda, F.tipo_de_cambio(mov.moneda))
        l.append("%s\n%s" % (monto, esc(mov.descripcion)))
        extra = []
        if getattr(mov, "cuenta", None) and mov.cuenta != "Gastos":
            extra.append("cuenta " + mov.cuenta)
        if mov.medio:
            extra.append(mov.medio + (" · " + mov.tarjeta.lower() if getattr(mov, "tarjeta", None) else ""))
        if mov.fecha != F.hoy():
            extra.append(mov.fecha.strftime("%d/%m/%Y"))
        if extra:
            l.append("<i>%s</i>" % esc(" · ".join(extra)))
        if mov.tipo == "Gasto" and getattr(mov, "tarjeta", None) == "Crédito" and DEUDAS in self.bases:
            d = F.cargar_a_tarjeta(self.notion, self.bases, mov.medio, mov.monto, mov.moneda)
            self._credito_de[pid] = (d["id"], d["cargo"])
            debe = F.s3(F.soles(d["saldo"], d["moneda"]))
            l.append("🧾 A crédito: %s %s. Ahora debes %s." % (
                "creé la deuda" if d["nueva"] else "se sumó a", esc(d["deuda"]), debe))
            if getattr(mov, "cuotas", None):
                primera = F.primer_mes_de_cuota(mov.fecha)
                l.append("📅 En %d cuotas de %s, la primera en %s." % (
                    mov.cuotas, self._en(round(mov.monto / mov.cuotas, 2), mov.moneda), F.mes_texto(primera)))
        mueve = mov.tipo == "Ingreso" or (mov.tipo == "Gasto" and getattr(mov, "tarjeta", None) != "Crédito")
        if mueve and mov.medio and PATRIMONIO in self.bases:
            cuenta = F.buscar_cuenta(self.notion, self.bases, mov.medio, mov.moneda)
            if cuenta:
                delta = mov.monto if mov.tipo == "Ingreso" else -mov.monto
                nuevo = F.mover_cuenta(self.notion, cuenta, delta)
                self._cuenta_de[pid] = (cuenta["id"], delta)
                l.append("🏦 %s ahora tiene %s" % (esc(cuenta["nombre"]), F.s3(F.soles(nuevo, cuenta["moneda"]))))
            else:
                l.append("<i>💡 Para que siga el saldo de %s en %s: <code>/activo %s 1000 %s</code> con lo que tengas hoy.</i>" % (
                    esc(mov.medio), mov.moneda, esc(mov.medio), mov.moneda.lower()))
        otra_cuenta = []
        if pid in self._cuenta_de:
            for banco in C.BILLETERA_OTROS.get(mov.medio, []):
                alt = F.buscar_cuenta(self.notion, self.bases, banco, mov.moneda)
                if alt and _pid(alt["id"]) != _pid(self._cuenta_de[pid][0]):
                    otra_cuenta.append(("🔁 Salió de %s" % alt["nombre"], "cb:%s:%s" % (pid, banco)))
        if meta:
            nuevo = F.sumar_a_meta(self.notion, meta, F.soles(mov.monto, mov.moneda))
            self._metas_de[pid] = (meta, F.soles(mov.monto, mov.moneda))
            avance = nuevo / meta["objetivo"] if meta["objetivo"] else None
            l.append("🎯 %s: %s de %s (%s)" % (esc(meta["meta"]), F.s(nuevo), F.s(meta["objetivo"]), F.pct(avance)))
        if mov.tipo == "Gasto":
            aviso = self._aviso_presupuesto(mov.categoria, getattr(mov, "frecuencia", None))
            if aviso:
                l.append(aviso)
            if mov.categoria not in C.CATEGORIAS_FIJAS:
                l.extend(I.limite_corto(F.estado_limite(self.notion, self.bases)))
        ti = C.TIPOS.index(mov.tipo)
        if not mov.adivinada:
            l.append("\n¿De qué categoría es?")
            self.decir(chat, "\n".join(l), self._botones_categoria(pid, ti) + [otra_cuenta, [("↩️ Deshacer", "x:" + pid)]])
        else:
            self.decir(chat, "\n".join(l), [otra_cuenta, [("🏷 Cambiar categoría", "k:%s:%d" % (pid, ti)), ("↩️ Deshacer", "x:" + pid)]])
        if mov.tipo == "Ingreso" and mov.categoria != "Retiro de ahorro":
            self._ofrecer_ahorro(chat, mov)
        if sus:
            self.decir(chat, "🔁 %s · %s · próximo pago %s" % (esc(r["nombre"]), F.cada_texto(r["cada"]), r["proximo"].strftime("%d/%m/%Y")))
        elif nueva_sus:
            self._preguntar_suscripcion(chat, pid, mov)

    # ---- suscripciones: la primera vez que se paga una, se pregunta cada cuanto se paga
    def _preguntar_suscripcion(self, chat, pid: str, mov) -> None:
        nombre = mov.descripcion if C.normal(mov.descripcion) != C.normal(F.CATEGORIA_SUSCRIPCIONES) else ""
        self._suscribiendo[chat] = {"pid": pid, "nombre": nombre, "monto": mov.monto, "moneda": mov.moneda, "fecha": mov.fecha}
        self.decir(chat, "🔁 <b>%s</b> es una suscripción nueva. ¿Cada cuánto se paga?\n"
                         "<i>Queda en tu lista y el presupuesto de Suscripciones se ajusta solo.</i>" % esc(nombre or "Esta"),
                   [[("Mensual", "sc:1"), ("Anual", "sc:12")], [("3 meses", "sc:3"), ("6 meses", "sc:6")],
                    [("✏️ Otro (meses)", "sc:x"), ("Pago único", "sc:no")]])

    def _boton_suscripcion(self, chat, valor: str) -> None:
        p = self._suscribiendo.get(chat)
        if not p:
            self.decir(chat, "Ese botón ya no sirve.")
            return
        if valor == "no":
            self._suscribiendo.pop(chat, None)
            self.decir(chat, "👌 Queda como un pago único, no como suscripción.")
        elif valor == "x":
            p["esperando"] = True
            self.decir(chat, "✏️ ¿Cada cuántos meses se paga? Escribe solo el número, por ejemplo <code>4</code>.")
        else:
            self._crear_suscripcion(chat, int(valor))

    def _meses_suscripcion(self, chat, texto: str) -> None:
        p = self._suscribiendo[chat]
        if not p.get("nombre") and p.get("pidiendo_nombre"):
            p["nombre"] = texto.strip()[:60]
            p.pop("esperando", None)
            self._crear_suscripcion(chat, p["cada"])
            return
        m = re.match(r"^\s*(\d{1,2})\s*(meses|mes)?\s*$", C.normal(texto))
        if not m or not 1 <= int(m.group(1)) <= 36:
            self.decir(chat, "Escribe solo el número de meses, por ejemplo <code>4</code>.", [[("Pago único", "sc:no")]])
            return
        p.pop("esperando", None)
        self._crear_suscripcion(chat, int(m.group(1)))

    def _crear_suscripcion(self, chat, cada: int) -> None:
        p = self._suscribiendo[chat]
        if not p.get("nombre"):
            p.update({"cada": cada, "esperando": True, "pidiendo_nombre": True})
            self.decir(chat, "📝 ¿Cómo se llama la suscripción? (por ejemplo: <i>Netflix</i>)")
            return
        self._suscribiendo.pop(chat, None)
        r = F.registrar_pago_suscripcion(self.notion, self.bases, p["nombre"], p["monto"], p["moneda"], cada, p["fecha"])
        if cada > 1:
            self.notion.editar_pagina(p["pid"], {"Frecuencia": p_select("Anual")})   # no infla el mes
        self.decir(chat, "🔁 Agregué <b>%s</b> (%s). Próximo pago: %s.\n%s" % (
            esc(r["nombre"]), F.cada_texto(cada), r["proximo"].strftime("%d/%m/%Y"),
            self._texto_tope_suscripciones(F.recalcular_presupuesto_suscripciones(self.notion, self.bases))))

    def _texto_tope_suscripciones(self, t: dict) -> str:
        l = "🧾 Tus suscripciones: %s al mes + %s al año (≈ %s al mes en total)" % (
            F.s(t["mensual"]), F.s(t["anual"]), F.s(t["por_mes"]))
        if t["tope"]:
            usado = t["por_mes"] / t["tope"]
            l += "\n%s Máximo: %s al mes · %s" % (
                F.marca_limite(usado), F.s(t["tope"]),
                "te pasas por %s" % F.s(t["por_mes"] - t["tope"]) if usado > 1 else "quedan %s" % F.s(t["tope"] - t["por_mes"]))
        return l

    def _suscripcion_cmd(self, chat, arg: str) -> None:
        m = re.match(r"(?i)\s*cancelar\s+(.+)$", arg or "")
        if not m:
            self.decir(chat, I.texto_suscripciones(self.notion, self.bases))
            return
        x = F.buscar_suscripcion(F.suscripciones(self.notion, self.bases), m.group(1))
        if not x:
            self.decir(chat, "No encuentro «%s» en tus suscripciones. Mira /suscripciones." % esc(m.group(1)))
            return
        self.notion.editar_pagina(x["id"], {"Estado": p_select("Cancelada")})
        self.decir(chat, "✖️ Cancelé %s.\n%s" % (esc(x["nombre"]), self._texto_tope_suscripciones(
            F.recalcular_presupuesto_suscripciones(self.notion, self.bases))))

    # ---- pagate primero: al cobrar, separar una parte para ahorro
    def _ofrecer_ahorro(self, chat, mov) -> None:
        self._por_ahorrar[chat] = {"monto": mov.monto, "moneda": mov.moneda, "medio": mov.medio}
        botones = []
        for pct in (10, 20):
            parte = round(mov.monto * pct / 100, 2)
            botones.append(("%d%% (%s)" % (pct, self._en(parte, mov.moneda)), "a:%d" % pct))
        self.decir(chat, "🐷 <b>¿Separas algo para ahorro?</b>\nPágate primero: lo que separas apenas cobras es lo que de verdad se ahorra.",
                   [botones, [("✏️ Otro monto", "a:x"), ("No esta vez", "a:no")]])

    @staticmethod
    def _en(monto: float, moneda: str) -> str:
        return F.s(monto) if moneda == "PEN" else "%s %s" % (moneda, "{:,.2f}".format(monto))

    def _boton_ahorro(self, chat, data: str) -> None:
        p = self._por_ahorrar.get(chat)
        if not p:
            self.decir(chat, "Ese botón ya no sirve.")
            return
        if data == "no":
            self._por_ahorrar.pop(chat, None)
            self.decir(chat, "👌 Todo queda disponible en la cuenta.")
        elif data == "x":
            p["esperando"] = True
            self.decir(chat, "✏️ ¿Cuánto separas? Escribe solo el número, en %s." % p["moneda"])
        elif data.startswith("m:"):
            self._ahorrar(chat, data[2:])
        else:
            p["separar"] = round(p["monto"] * int(data) / 100, 2)
            self._elegir_meta(chat)

    def _monto_a_ahorrar(self, chat, texto: str) -> None:
        p = self._por_ahorrar[chat]
        try:
            n = _numero(texto.replace(" ", "").lstrip("S/$€₽").strip())
        except ValueError:
            n = 0
        if n <= 0:
            self.decir(chat, "Escribe solo el número, por ejemplo <code>150</code>.", [[("No esta vez", "a:no")]])
            return
        p.pop("esperando", None)
        p["separar"] = round(n, 2)
        self._elegir_meta(chat)

    def _elegir_meta(self, chat) -> None:
        p = self._por_ahorrar[chat]
        nombres = self._nombres_metas()
        p["metas"] = nombres
        botones = [[("🎯 " + n, "a:m:%d" % k)] for k, n in enumerate(nombres)]
        botones.append([("🐷 Ahorro general", "a:m:g")])
        extra = "" if nombres else "\n<i>Aún no tienes metas; puedes crear una con /meta Emergencia 10000</i>"
        self.decir(chat, "¿Para qué es lo que separas (%s)?%s" % (self._en(p["separar"], p["moneda"]), extra), botones)

    def _ahorrar(self, chat, cual: str) -> None:
        p = self._por_ahorrar.pop(chat, None)
        if not p or "separar" not in p:
            self.decir(chat, "Ese botón ya no sirve.")
            return
        meta = None if cual == "g" else p["metas"][int(cual)]
        mov = Movimiento(tipo="Ahorro", monto=p["separar"], moneda=p["moneda"],
                         descripcion="Ahorro para %s" % meta if meta else "Ahorro",
                         categoria="Fondo de emergencia" if meta and "emergencia" in C.normal(meta) else "Metas" if meta else "Ahorro general",
                         medio=p["medio"], fecha=F.hoy())
        self._guardar(chat, mov, meta)

    def _aviso_presupuesto(self, categoria: str, frecuencia: Optional[str] = None) -> str:
        """Si con este gasto la categoria pasa del 80% o del 100% de su presupuesto: el mensual,
        o el anual si es un pago anual."""
        try:
            if frecuencia == "Anual":
                plan = F.presupuesto_anual(self.notion, self.bases)
                if categoria not in plan:
                    return "⚠️ Pago anual de %s fuera del presupuesto (no tiene tope anual)." % esc(categoria)
                g, tope = F.pagado_anual(self.notion, self.bases, categoria), plan[categoria]
                if g > tope:
                    return "🔴 Pasaste el presupuesto anual de %s: %s de %s este año." % (esc(categoria), F.s(g), F.s(tope))
                return "%s Pagos anuales de %s: %s de %s este año (quedan %s)." % (
                    "🟡" if g >= 0.8 * tope else "🟢", esc(categoria), F.s(g), F.s(tope), F.s(tope - g))
            plan = F.presupuesto(self.notion, self.bases)
            if F.fuera_de_presupuesto(categoria, plan):
                return "⚠️ Fuera del presupuesto: %s no tiene tope mensual. Si es un gasto que se repite, ponle uno: <code>/presupuesto %s 100</code>" % (
                    esc(categoria), esc(categoria.split()[0].lower()))
            if categoria not in plan:
                return ""
            m = F.mes()
            g = F.resumir(F.movimientos(self.notion, self.bases, m.desde, F.hoy()), m).mensuales.get(categoria, 0)
        except NotionError:
            return ""
        tope = plan[categoria]
        if g >= tope:
            return "🔴 Pasaste el presupuesto de %s: %s de %s." % (esc(categoria), F.s(g), F.s(tope))
        if g >= 0.8 * tope:
            return "🟡 %s va en %s del presupuesto (quedan %s)." % (esc(categoria), F.pct(g / tope), F.s(tope - g))
        return ""

    def _botones_categoria(self, pid: str, ti: int) -> list:
        cats = C.nombres(C.TIPOS[ti])
        botones = [("%s %s" % (C.emoji(C.TIPOS[ti], c), c), "c:%s:%d:%d" % (pid, ti, k)) for k, c in enumerate(cats)]
        return [botones[i:i + 2] for i in range(0, len(botones), 2)]

    # ---- botones
    def _boton(self, chat, message_id, data: str) -> None:
        partes = data.split(":")
        try:
            if partes[0] == "f":
                if data == "f:ok":
                    if not self.form.listo(chat):
                        self.decir(chat, "Ese formulario ya terminó.")
                        return
                    self.tg.quitar_botones(chat, message_id)
                    mov, meta = self.form.terminar(chat)
                    self._guardar(chat, mov, meta)
                else:
                    self.tg.quitar_botones(chat, message_id)
                    self._responder(chat, self.form.boton(chat, data[2:]))
            elif partes[0] == "m" and partes[1] == "ver":
                self.decir(chat, "👁 <b>¿Qué quieres ver?</b>", MENU_VER)
            elif partes[0] == "m" and partes[1] == "ajustar":
                self.decir(chat, "⚙️ <b>¿Qué quieres ajustar?</b>", MENU_AJUSTAR)
            elif partes[0] == "m":
                self._comando(chat, "/" + partes[1])
            elif partes[0] == "aj":
                self.tg.quitar_botones(chat, message_id)
                if partes[1] == "no":
                    self._ajustando.pop(chat, None)
                    self.decir(chat, "👌 Nada que ajustar.")
                elif partes[1] in AJUSTES_BOT:
                    self._ajustando[chat] = AJUSTES_BOT[partes[1]][1]
                    self.decir(chat, AJUSTES_BOT[partes[1]][2], [[("✖️ Cancelar", "aj:no")]])
            elif partes[0] == "k" and len(partes) == 3:
                self.decir(chat, "Elige la categoría:", self._botones_categoria(partes[1], int(partes[2])))
            elif partes[0] == "c" and len(partes) == 4:
                self.tg.quitar_botones(chat, message_id)
                tipo = C.TIPOS[int(partes[2])]
                cat = C.nombres(tipo)[int(partes[3])]
                F.cambiar_categoria(self.notion, partes[1], tipo, cat)
                aviso = self._aviso_presupuesto(cat) if tipo == "Gasto" else ""
                self.decir(chat, "🏷 Listo: %s %s%s" % (C.emoji(tipo, cat), esc(cat), "\n" + aviso if aviso else ""))
            elif partes[0] == "rc" and len(partes) == 3:
                self.tg.quitar_botones(chat, message_id)
                self._boton_recordatorio(chat, partes[1], partes[2])
            elif partes[0] == "sc":
                self.tg.quitar_botones(chat, message_id)
                self._boton_suscripcion(chat, partes[1])
            elif partes[0] in ("pg", "pm", "pc"):
                self.tg.quitar_botones(chat, message_id)
                self._boton_pago(chat, partes[0], ":".join(partes[1:]))
            elif partes[0] == "cb" and len(partes) == 3:
                self.tg.quitar_botones(chat, message_id)
                self._cambiar_cuenta(chat, partes[1], partes[2])
            elif partes[0] == "rt":
                self.tg.quitar_botones(chat, message_id)
                self._boton_retiro(chat, partes[1])
            elif partes[0] == "a":
                self.tg.quitar_botones(chat, message_id)
                self._boton_ahorro(chat, data[2:])
            elif partes[0] == "x" and len(partes) == 2:
                self.tg.quitar_botones(chat, message_id)
                self._deshacer(chat, partes[1])
            elif partes[0] == "mv" and len(partes) == 2:
                self._ver_movimiento(chat, partes[1])
            elif partes[0] == "me" and len(partes) == 2:
                self.tg.quitar_botones(chat, message_id)
                self._pedir_monto(chat, partes[1])
            elif partes[0] == "mb" and len(partes) == 2:
                self.tg.quitar_botones(chat, message_id)
                self._deshacer(chat, partes[1])
            elif partes[0] == "mn":
                self.tg.quitar_botones(chat, message_id)
                self._corrigiendo.pop(chat, None)
                self.decir(chat, "👌 Lo dejo como está.")
        except (ValueError, IndexError):
            self.decir(chat, "Ese botón ya no sirve. Escribe /ayuda.")
        except NotionError as exc:
            self.decir(chat, "⚠️ Notion no respondió: %s" % esc(str(exc)[:200]))

    def _cambiar_cuenta(self, chat, pid: str, banco: str) -> None:
        """Yape salio de Interbank y no de BCP: devuelve la plata a la primera cuenta y la saca de la otra."""
        if pid not in self._cuenta_de:
            self.decir(chat, "Ese botón ya no sirve. Corrige el saldo con <code>/activo</code>.")
            return
        cuenta_id, delta = self._cuenta_de[pid]
        todas = {_pid(c["id"]): c for c in F.cuentas(self.notion, self.bases)}
        antes = todas.get(_pid(cuenta_id))
        alt = F.buscar_cuenta(self.notion, self.bases, banco, antes["moneda"] if antes else "PEN")
        if not alt:
            self.decir(chat, "No encuentro la cuenta de %s. Créala con <code>/activo %s 1000</code>." % (esc(banco), esc(banco)))
            return
        l = []
        if antes:
            l.append("🏦 %s vuelve a %s" % (esc(antes["nombre"]), F.s3(F.soles(F.mover_cuenta(self.notion, antes, -delta), antes["moneda"]))))
        nuevo = F.mover_cuenta(self.notion, alt, delta)
        self._cuenta_de[pid] = (alt["id"], delta)
        l.append("🏦 %s ahora tiene %s" % (esc(alt["nombre"]), F.s3(F.soles(nuevo, alt["moneda"]))))
        self.decir(chat, "🔁 Listo, salió de %s.\n%s" % (esc(alt["nombre"]), "\n".join(l)))

    def _deshacer(self, chat, pid: str) -> None:
        """Borra el movimiento y deshace lo que movió. Funciona con cualquiera, no solo el último."""
        mov = F.movimiento(self.notion, self.bases, pid)
        self.notion.archivar(pid)
        l = self._quitar_efectos(mov, pid) if mov else []
        if self._ultimo.get(chat) == pid:
            self._ultimo.pop(chat, None)
        self._corrigiendo.pop(chat, None)
        self.decir(chat, "\n".join(["🗑 Borrado. (Queda en la papelera de Notion por 30 días.)"] + l))

    # ---- comandos
    def _comando(self, chat, texto: str) -> None:
        partes = texto.split(maxsplit=1)
        cmd = C.normal(partes[0].split("@")[0])
        arg = partes[1].strip() if len(partes) > 1 else ""
        forzar = {"/gasto": "Gasto", "/ingreso": "Ingreso", "/ahorro": "Ahorro", "/inversion": "Inversión"}
        if cmd in ("/start", "/menu", "/inicio"):
            self.decir(chat, self._inicio(), MENU)
        elif cmd in ("/ayuda", "/help", "/comandos"):
            self.decir(chat, AYUDA, MENU)
        elif cmd == "/id":
            self.decir(chat, "Tu chat es <code>%s</code>." % esc(chat))
        elif cmd in forzar:
            if not arg:
                self._responder(chat, self.form.iniciar(chat, cmd[1:]))
            else:
                self._anotar(chat, arg, forzar[cmd])
        elif cmd in ("/hoy", "/ayer", "/semana", "/mes"):
            p = {"/hoy": F.dia(), "/ayer": F.dia(F.hoy() - timedelta(days=1)), "/semana": F.semana(), "/mes": F.mes()}[cmd]
            inf = I.Informe(self.notion, self.bases, p)
            self.decir(chat, inf.texto(), MENU)
        elif cmd == "/presupuesto":
            self._presupuesto(chat, arg)
        elif cmd == "/patrimonio":
            self.decir(chat, I.texto_patrimonio(self.notion, self.bases))
        elif cmd == "/deuda" and DEUDAS in self.bases:
            self._deuda(chat, arg)
        elif cmd in ("/activo", "/deuda"):
            self._patrimonio(chat, "Activo" if cmd == "/activo" else "Pasivo", arg)
        elif cmd == "/deudas":
            self.decir(chat, I.texto_deudas(self.notion, self.bases), self._botones_pagar())
        elif cmd in ("/retirar", "/retiro", "/efectivo"):
            self._retirar(chat)
        elif cmd in ("/pago", "/pagar"):
            self._pago(chat, arg)
        elif cmd == "/metas":
            self.decir(chat, I.texto_metas(self.notion, self.bases))
        elif cmd == "/meta":
            self._meta(chat, arg)
        elif cmd == "/consejos":
            inf = I.Informe(self.notion, self.bases, F.mes())
            lista = inf.consejos or ["🟢 No veo nada preocupante este mes. Sigue anotando todo."]
            self.decir(chat, "💡 <b>Qué mejorar</b> (con lo que va de %s)\n\n%s\n\nMás ideas: /metodos" % (
                F.MESES[F.hoy().month - 1], "\n\n".join(esc(c) for c in lista)))
        elif cmd in ("/pagos", "/recordatorios", "/fijos"):
            self._pagos(chat)
        elif cmd in ("/proyeccion", "/proyección"):
            self.decir(chat, I.texto_proyeccion(self.notion, self.bases))
        elif cmd == "/plan":
            self._plan(chat, arg)
        elif cmd == "/ingresos":
            self.decir(chat, I.texto_ingresos(self.notion, self.bases))
        elif cmd in ("/grafico", "/gráfico"):
            self._grafico(chat)
        elif cmd in ("/suscripciones", "/suscripcion"):
            self._suscripcion_cmd(chat, arg)
        elif cmd in ("/limite", "/limites"):
            self._limite(chat, arg)
        elif cmd in ("/excel", "/graficos"):
            self._excel(chat)
        elif cmd in ("/metodos", "/opciones"):
            self.decir(chat, METODOS)
        elif cmd == "/tc":
            self._tc(chat, arg)
        elif cmd in ("/buscar", "/busca"):
            self._buscar(chat, arg)
        elif cmd == "/ultimos":
            self._ultimos(chat)
        elif cmd == "/deshacer":
            pid = self._ultimo.get(chat)
            if not pid:
                self.decir(chat, "No hay nada reciente para deshacer. Mira /ultimos y bórralo en Notion.")
            else:
                self._deshacer(chat, pid)
        elif cmd == "/cancelar":
            if self._retirando.pop(chat, None):
                self.decir(chat, "👌 No retiré nada.")
            elif self._suscribiendo.pop(chat, None):
                self.decir(chat, "👌 Queda como un pago único.")
            elif self._pagando.pop(chat, None):
                self.decir(chat, "👌 No registré ningún pago.")
            elif self._por_ahorrar.pop(chat, None):
                self.decir(chat, "👌 No separo nada esta vez.")
            elif self.form.activo(chat):
                self._responder(chat, self.form.cancelar(chat))
            else:
                self.decir(chat, "No hay nada en curso. 🙂")
        else:
            self.decir(chat, "No conozco ese comando.", MENU)

    def _presupuesto(self, chat, arg: str) -> None:
        if not arg:
            self.decir(chat, I.texto_presupuesto(self.notion, self.bases))
            return
        anual = bool(re.search(r"\banual\b", C.normal(arg)))
        arg = re.sub(r"(?i)\banual\b", " ", arg).strip()
        m = re.match(r"(.+?)\s+(\d[\d.,]*)\s*$", arg)
        if not m:
            self.decir(chat, "Escribe la categoría y el monto: <code>/presupuesto comida 800</code> (al mes) · "
                             "<code>/presupuesto suscripciones anual 600</code> (pagos de una vez al año)")
            return
        cat = C.buscar_categoria("Gasto", m.group(1))
        if not cat:
            self.decir(chat, "No reconozco la categoría «%s». Las que hay:\n%s" % (
                esc(m.group(1)), esc(", ".join(C.nombres("Gasto")))))
            return
        monto = _numero(m.group(2))
        F.fijar_presupuesto(self.notion, self.bases, cat, monto, "Anual S/" if anual else "Mensual S/")
        if anual:
            self.decir(chat, "🧾 Pagos anuales de %s %s: %s al año.\nCuando anotes uno, toca <b>Anual</b> en el formulario "
                             "o escribe la palabra <i>anual</i>: <code>120 icloud anual</code>" % (C.emoji("Gasto", cat), esc(cat), F.s3(monto)))
        else:
            self.decir(chat, "🧾 Presupuesto de %s %s: %s al mes." % (C.emoji("Gasto", cat), esc(cat), F.s3(monto)))

    def _patrimonio(self, chat, clase: str, arg: str) -> None:
        if not arg:
            ej = "/activo Interbank 5200 · /activo Binance 800 usd · /activo Auto 45000" if clase == "Activo" else "/deuda Tarjeta Falabella 1200 · /deuda Préstamo BCP 15000"
            self.decir(chat, "Escribe el nombre y el valor actual: <code>%s</code>" % esc(ej))
            return
        try:
            nombre, valor, moneda, tipo = leer_patrimonio(clase, arg)
        except NoEntendi as exc:
            self.decir(chat, esc(exc))
            return
        _, antes = F.fijar_patrimonio(self.notion, self.bases, nombre, clase, tipo, valor, moneda)
        ahora = F.soles(valor, moneda)
        cambio = ""
        if antes is not None:
            d = ahora - float(antes)
            cambio = " (antes %s, %s%s)" % (F.s(antes), "+" if d >= 0 else "", F.s(d))
        _, _, net, _ = F.neto(F.patrimonio(self.notion, self.bases))
        self.decir(chat, "%s %s · %s: %s%s\n🏦 Patrimonio neto: <b>%s</b>" % (
            "🟢" if clase == "Activo" else "🔻", esc(nombre), esc(tipo), F.s3(ahora), cambio, F.s3(net)))

    def _inicio(self) -> str:
        """La pantalla de inicio: arriba, cuanto puedes gastar y cuanto llevas; despues lo importante."""
        hoy = F.hoy()
        l = ["💰 <b>Finanzas</b> · %s %d de %s" % (["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"][hoy.weekday()],
                                               hoy.day, F.MESES[hoy.month - 1].lower()), ""]
        try:
            lim = F.estado_limite(self.notion, self.bases)
            if lim:
                # primera linea: lo que queda hoy, lo primero que se ve
                x, tc = lim["dia"], F.tipo_de_cambio(lim["moneda"])
                l[0] = "📏 %s hoy: %s" % ("Te pasaste" if x["queda"] < 0 else "Quedan", F.s3(abs(x["queda"]) * tc))
                l[1] = "💰 <b>Finanzas</b> · %s %d de %s\n" % (["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"][hoy.weekday()],
                                                           hoy.day, F.MESES[hoy.month - 1].lower())
                l.append("📏 <b>Para gastar en el día a día</b>")
                l.extend(I.lineas_limite(lim))
            else:
                l.append("📏 Fija cuánto puedes gastar por día y aquí verás cuánto te queda hoy, en la semana y en el mes: "
                         "<code>/limite 1500 rub</code>")
            deudas = F.deudas(self.notion, self.bases)
            if deudas:
                cuotas = sum(F.soles(d["cuota"], d["moneda"]) for d in deudas if d["cuota"])
                l.append("")
                l.append("💳 Deudas: <b>%s</b>%s" % (F.s3(sum(d["saldo_s"] for d in deudas)),
                                                    " · cuotas %s al mes" % F.s(cuotas) if cuotas else ""))
            metas = [m for m in F.metas(self.notion, self.bases) if m["avance"] < 1]
            if metas:
                l.append("🎯 " + " · ".join("%s %s" % (esc(m["meta"]), F.pct(m["avance"])) for m in metas[:4]))
            for r in F.avisos_de_hoy(self.notion, self.bases, hoy):
                l.append("🔔 Hoy toca: %s%s" % (esc(r["nombre"]), I.monto_rec(r)))
            pro = F.proyeccion(self.notion, self.bases, hoy)
            if pro:
                l.append("%s Si no entra más dinero, cierras el mes con %s" % ("📈" if pro["cierre"] >= 0 else "📉", F.s3(pro["cierre"])))
            for x in F.renovaciones(self.notion, self.bases, hoy, 3):
                l.append("🔁 %s se renueva el %s" % (esc(x["nombre"]), "/".join(reversed(x["proximo"][5:10].split("-")))))
        except NotionError:
            l.append("<i>⚠️ Notion no respondió; prueba /start en un rato.</i>")
        l.append("")
        l.append("Anotar: /gasto · /ingreso · /ahorro · /inversion\nTodos los comandos: /ayuda")
        return "\n".join(l)

    # ---- pagos del mes, proyeccion, plan de deudas y grafico
    def _botones_recordatorios(self, lista: list) -> list:
        import avisos
        filas = []
        for r in lista[:10]:
            hacer = avisos.botones_aviso(r)[0][0]
            filas.append([("%s · %s" % (hacer[0], r["nombre"]), hacer[1])])
        return filas

    def _pagos(self, chat) -> None:
        pend = F.pendientes_del_mes(self.notion, self.bases)
        self.decir(chat, I.texto_pagos(self.notion, self.bases), self._botones_recordatorios(pend) or None)

    def _boton_recordatorio(self, chat, accion: str, rid: str) -> None:
        r = next((x for x in F.recordatorios(self.notion, self.bases) if _pid(x["id"]) == rid), None)
        if not r:
            self.decir(chat, "Ese recordatorio ya no existe. Mira /pagos.")
            return
        if accion == "m":
            dia = F.posponer(r["id"])
            self.decir(chat, "⏰ Te lo recuerdo mañana (%s): %s" % (dia.strftime("%d/%m"), esc(r["nombre"])))
            return
        if accion == "d":
            d = F.buscar_deuda(F.deudas(self.notion, self.bases), r["deuda"])
            if not d:
                self.decir(chat, "No encuentro la deuda «%s». Mira /deudas." % esc(r["deuda"]))
                return
            F.marcar_hecho(self.notion, r)
            self._registrar_pago(chat, d, r["monto"] or d["cuota"] or d["saldo"], r["moneda"] if r["monto"] else None)
            return
        if accion == "p":
            mov = Movimiento(tipo="Gasto", monto=r["monto"], moneda=r["moneda"], descripcion=r["nombre"],
                             categoria=r["categoria"], fecha=F.hoy(), cuenta="Gastos")
            F.marcar_hecho(self.notion, r)
            self._guardar(chat, mov)
            return
        F.marcar_hecho(self.notion, r)
        self.decir(chat, "✅ Listo: %s (marcado este mes)." % esc(r["nombre"]))

    def _plan(self, chat, arg: str) -> None:
        extra, txt = None, ""
        m = re.search(r"\d[\d.,]*", arg or "")
        if m:
            moneda = next((v for k, v in MONEDAS.items() if k in C.normal(arg).split()), "PEN")
            n = _numero(m.group(0))
            extra, txt = F.soles(n, moneda), F.en_moneda(n, moneda)
        self.decir(chat, I.texto_plan(self.notion, self.bases, extra, txt))

    def _buscar(self, chat, arg: str) -> None:
        """/buscar farmacia · /buscar uber mes · /buscar netflix año"""
        if not arg.strip():
            self.decir(chat, "🔍 Escribe qué buscar:\n<code>/buscar farmacia</code>\n"
                             "<code>/buscar uber mes</code> · solo este mes\n"
                             "<code>/buscar netflix año</code> · solo este año")
            return
        palabras, periodo = [], None
        for w in arg.split():
            wn = C.normal(w).strip(".,")
            if wn in ("mes", "semana", "ano", "anio") and periodo is None:
                periodo = wn
            else:
                palabras.append(w)
        texto = " ".join(palabras)
        if not texto:
            self.decir(chat, "🔍 Falta qué buscar. Por ejemplo <code>/buscar farmacia mes</code>.")
            return
        d = F.hoy()
        if periodo == "mes":
            p = F.mes(d)
            desde, hasta, cuando = p.desde, p.hasta, p.titulo.lower()
        elif periodo == "semana":
            p = F.semana(d)
            desde, hasta, cuando = p.desde, p.hasta, "esta semana"
        elif periodo:
            desde, hasta, cuando = d.replace(month=1, day=1), d, str(d.year)
        else:
            desde, hasta, cuando = None, None, ""
        self.decir(chat, I.texto_buscar(self.notion, self.bases, texto, desde, hasta, cuando))

    def _grafico(self, chat) -> None:
        url = I.url_grafico_semana(self.notion, self.bases)
        if not url:
            self.decir(chat, "🖼 Esta semana todavía no hay gastos para graficar.")
            return
        try:
            self.tg.enviar_foto(chat, url, "🖼 Tus gastos de la semana por categoría")
        except TelegramError as exc:
            self.decir(chat, "⚠️ No pude mandar el gráfico: %s" % esc(str(exc)[:200]))

    def _limite(self, chat, arg: str) -> None:
        if not arg:
            self.decir(chat, I.texto_limite(self.notion, self.bases))
            return
        m = re.search(r"\d[\d.,]*", arg)
        if not m:
            self.decir(chat, "Escribe cuánto puedes gastar por día: <code>/limite 1500 rub</code>")
            return
        moneda = next((v for k, v in MONEDAS.items() if k in C.normal(arg).split()), "PEN")
        F.fijar_limite(_numero(m.group(0)), moneda)
        if not F.limite():
            self.decir(chat, "👌 Quité el límite del día a día.")
            return
        self.decir(chat, "📏 Listo.\n\n" + I.texto_limite(self.notion, self.bases))

    def _excel(self, chat) -> None:
        self.decir(chat, "📊 Preparando tu Excel…")
        try:
            contenido = X.libro(self.notion, self.bases)
            self.tg.enviar_documento(chat, X.nombre_archivo(), contenido,
                                     "📊 Tus finanzas al %s, con gráficos en cada hoja: Resumen, Deudas, Cuentas, "
                                     "Metas, Presupuesto, Por mes, Categorías y Movimientos." % F.hoy().strftime("%d/%m/%Y"))
        except TelegramError as exc:
            self.decir(chat, "⚠️ No pude mandar el archivo: %s" % esc(str(exc)[:200]))

    def _deuda(self, chat, arg: str) -> None:
        if not arg:
            self.decir(chat, "Escribe el nombre y lo que debes hoy: <code>/deuda Tarjeta Falabella 1200</code> · "
                             "<code>/deuda Préstamo BCP 15000</code> · <code>/deuda Juan 200 usd</code>")
            return
        try:
            nombre, saldo, moneda, tipo = leer_patrimonio("Pasivo", arg)
        except NoEntendi as exc:
            self.decir(chat, esc(str(exc).replace("/activo Interbank 5200", "/deuda Tarjeta Falabella 1200")))
            return
        _, antes = F.fijar_deuda(self.notion, self.bases, nombre, tipo, saldo, moneda)
        ahora = F.soles(saldo, moneda)
        cambio = ""
        if antes is not None:
            d = ahora - float(antes)
            cambio = " (antes %s, %s%s)" % (F.s(antes), "+" if d >= 0 else "", F.s(d))
        total = sum(x["saldo_s"] for x in F.deudas(self.notion, self.bases))
        self.decir(chat, "💳 %s · %s: %s%s\nTotal de deudas: <b>%s</b>\n"
                         "<i>En Notion (Deudas) puedes poner la tasa, la cuota y el día de pago.</i>" % (
                             esc(nombre), esc(tipo), F.s3(ahora), cambio, F.s3(total)))

    def _pago(self, chat, arg: str) -> None:
        lista = F.deudas(self.notion, self.bases)
        m = re.match(r"(.+?)\s+(\d[\d.,]*)(\s*k)?(?:\s+(\S+))?\s*$", arg)
        if not m:
            if not lista:
                self.decir(chat, "No tienes deudas activas. 🎉")
                return
            self.decir(chat, "💸 ¿A qué deuda le pagaste?\n<i>También puedes escribir: <code>/pago Falabella 300</code></i>",
                       self._botones_pagar(lista))
            return
        d = F.buscar_deuda(lista, m.group(1))
        if not d:
            self.decir(chat, "No encuentro la deuda «%s». Mira /deudas." % esc(m.group(1)))
            return
        moneda = MONEDAS.get(C.normal(m.group(4) or ""), None)
        monto = _numero(m.group(2)) * (1000 if m.group(3) else 1)
        self._registrar_pago(chat, d, monto, moneda)

    # ---- pagar una deuda con botones: deuda -> cuanto -> de que cuenta salio
    def _botones_pagar(self, lista=None) -> list:
        lista = F.deudas(self.notion, self.bases) if lista is None else lista
        return [[("💸 Pagar %s" % d["deuda"], "pg:" + _pid(d["id"]))] for d in lista[:12]]

    def _boton_pago(self, chat, clave: str, valor: str) -> None:
        if clave == "pg":
            d = next((x for x in F.deudas(self.notion, self.bases) if _pid(x["id"]) == valor), None)
            if not d:
                self.decir(chat, "Esa deuda ya no está activa. Mira /deudas.")
                return
            self._pagando[chat] = {"deuda": d}
            botones = []
            if d["cuota"]:
                botones.append(("Cuota (%s)" % self._en(d["cuota"], d["moneda"]), "pm:c"))
            botones.append(("Todo (%s)" % self._en(d["saldo"], d["moneda"]), "pm:t"))
            self.decir(chat, "💸 <b>%s</b>: debes %s\n¿Cuánto pagaste?" % (esc(d["deuda"]), F.s3(d["saldo_s"])),
                       [botones, [("✏️ Otro monto", "pm:x"), ("✖️ Cancelar", "pm:no")]])
            return
        p = self._pagando.get(chat)
        if not p:
            self.decir(chat, "Ese botón ya no sirve. Toca 💳 Deudas de nuevo.")
            return
        d = p["deuda"]
        if clave == "pm":
            if valor == "no":
                self._pagando.pop(chat, None)
                self.decir(chat, "👌 No registré ningún pago.")
            elif valor == "x":
                p["esperando"] = True
                self.decir(chat, "✏️ ¿Cuánto pagaste a %s? Escribe solo el número, en %s." % (esc(d["deuda"]), d["moneda"]))
            else:
                self._pagando.pop(chat, None)
                self._registrar_pago(chat, d, d["cuota"] if valor == "c" else d["saldo"])
        elif clave == "pc":
            self._pagando.pop(chat, None)
            if valor == "no":
                self.decir(chat, "👌 Listo, no toqué ninguna cuenta.")
                return
            c = p["cuentas"][int(valor)]
            nuevo = F.mover_cuenta(self.notion, c, -round(p["pago_s"] / F.tipo_de_cambio(c["moneda"]), 2))
            self.decir(chat, "🏦 %s ahora tiene %s" % (esc(c["nombre"]), F.s3(F.soles(nuevo, c["moneda"]))))

    def _monto_pagado(self, chat, texto: str) -> None:
        p = self._pagando[chat]
        try:
            n = _numero(texto.replace(" ", "").lstrip("S/$€₽").strip())
        except ValueError:
            n = 0
        if n <= 0:
            self.decir(chat, "Escribe solo el número, por ejemplo <code>500</code>.", [[("✖️ Cancelar", "pm:no")]])
            return
        self._pagando.pop(chat, None)
        self._registrar_pago(chat, p["deuda"], n)

    def _registrar_pago(self, chat, d: dict, monto: float, moneda: Optional[str] = None) -> None:
        """Baja la deuda y pregunta de que cuenta salio la plata (para bajar tambien esa cuenta)."""
        nuevo = F.pagar_deuda(self.notion, d, monto, moneda)
        if nuevo <= 0:
            self.decir(chat, "🎉 ¡%s pagada por completo! Ya no aparece en tus deudas." % esc(d["deuda"]))
        else:
            self.decir(chat, "✅ Pago a %s. Te queda: <b>%s</b>" % (esc(d["deuda"]), F.s3(F.soles(nuevo, d["moneda"]))))
        cuentas = F.cuentas(self.notion, self.bases)
        if cuentas:
            self._pagando[chat] = {"deuda": d, "pago_s": F.soles(monto, moneda or d["moneda"]), "cuentas": cuentas}
            botones = [[("🏦 %s (%s)" % (c["nombre"], self._en(c["valor"], c["moneda"])), "pc:%d" % k)]
                       for k, c in enumerate(cuentas[:10])]
            self.decir(chat, "¿De qué cuenta salió el pago?", botones + [[("No descontar", "pc:no")]])

    # ---- retirar efectivo: de que cuenta -> cuanto. Baja el banco y sube "Efectivo" (no es gasto)
    def _retirar(self, chat) -> None:
        bancos = [c for c in F.cuentas(self.notion, self.bases) if not F.es_efectivo(c)]
        if not bancos:
            self.decir(chat, "🏧 Primero registra el saldo de tus cuentas: <code>/activo Interbank soles 463</code>")
            return
        self._retirando[chat] = {"cuentas": bancos}
        botones = [[("🏦 %s (%s)" % (c["nombre"], self._en(c["valor"], c["moneda"])), "rt:%d" % k)]
                   for k, c in enumerate(bancos[:10])]
        self.decir(chat, "🏧 <b>Retirar efectivo</b>\n¿De qué cuenta sacaste la plata?", botones + [[("✖️ Cancelar", "rt:no")]])

    def _boton_retiro(self, chat, valor: str) -> None:
        if valor == "u":
            self._deshacer_retiro(chat)
            return
        r = self._retirando.get(chat)
        if valor == "no" or not r:
            self._retirando.pop(chat, None)
            self.decir(chat, "👌 No retiré nada." if valor == "no" else "Ese botón ya no sirve. Toca 🏧 Retirar efectivo de nuevo.")
            return
        c = r["cuentas"][int(valor)]
        self._retirando[chat] = {"cuenta": c, "esperando": True}
        self.decir(chat, "🏧 ¿Cuánto retiraste de %s? Escribe solo el número, en %s." % (esc(c["nombre"]), c["moneda"]),
                   [[("✖️ Cancelar", "rt:no")]])

    def _monto_retiro(self, chat, texto: str) -> None:
        c = self._retirando[chat]["cuenta"]
        try:
            n = _numero(texto.replace(" ", "").lstrip("S/$€₽").strip())
        except ValueError:
            n = 0
        if n <= 0:
            self.decir(chat, "Escribe solo el número, por ejemplo <code>200</code>.", [[("✖️ Cancelar", "rt:no")]])
            return
        self._retirando.pop(chat, None)
        banco, ef, efectivo = F.retirar_efectivo(self.notion, self.bases, c, n)
        self._retiro_de[chat] = (c["id"], ef["id"], n)
        l = ["🏧 Retiraste <b>%s</b> de %s" % (self._en(n, c["moneda"]), esc(c["nombre"])),
             "🏦 %s ahora tiene %s" % (esc(c["nombre"]), F.s3(F.soles(banco, c["moneda"]))),
             "💵 %s ahora tiene %s" % (esc(ef["nombre"]), F.s3(F.soles(efectivo, c["moneda"]))),
             "<i>No cuenta como gasto. Cuando pagues en efectivo, elige el medio Efectivo y se descuenta de ahí.</i>"]
        if banco < 0:
            l.insert(2, "⚠️ El saldo de %s quedó en negativo; corrígelo con <code>/activo %s monto</code>." % (
                esc(c["nombre"]), esc(c["nombre"])))
        self.decir(chat, "\n".join(l), [[("↩️ Deshacer retiro", "rt:u")]])

    def _deshacer_retiro(self, chat) -> None:
        ult = self._retiro_de.pop(chat, None)
        if not ult:
            self.decir(chat, "No hay ningún retiro para deshacer.")
            return
        banco_id, ef_id, n = ult
        todas = {_pid(x["id"]): x for x in F.cuentas(self.notion, self.bases)}
        if _pid(banco_id) in todas:
            F.mover_cuenta(self.notion, todas[_pid(banco_id)], n)
        if _pid(ef_id) in todas:
            F.mover_cuenta(self.notion, todas[_pid(ef_id)], -n)
        self.decir(chat, "↩️ Retiro deshecho: la plata volvió a la cuenta.")

    def _meta(self, chat, arg: str) -> None:
        m = re.match(r"(.+?)\s+(\d[\d.,]*)(\s*k)?\s*$", arg)
        if not m:
            self.decir(chat, "Escribe el nombre y el objetivo: <code>/meta Fondo de emergencia 20000</code>")
            return
        objetivo = _numero(m.group(2)) * (1000 if m.group(3) else 1)
        F.fijar_meta(self.notion, self.bases, m.group(1).strip(), objetivo)
        self.decir(chat, "🎯 Meta «%s»: %s.\nCuando ahorres escribe <code>ahorro 500 %s</code>" % (
            esc(m.group(1).strip()), F.s3(objetivo), esc(m.group(1).strip().split()[0].lower())))

    def _texto_tc(self) -> str:
        auto = F.tc_automatico()
        l = ["💱 <b>Tipo de cambio</b>"]
        for m, nombre in (("USD", "dólar"), ("RUB", "rublo"), ("EUR", "euro")):
            fijo = F.tc_fijo(m)
            if fijo:
                origen = "fijado por ti"
            elif auto.get(m):
                origen = "del día, actualizado %s" % auto.get("fecha", "")
            else:
                origen = "de respaldo (no pude bajar el del día)"
            l.append("1 %s = S/ %s · <i>%s</i>" % (nombre, F.tipo_de_cambio(m), origen))
        usd, rub = F.tipo_de_cambio("USD"), F.tipo_de_cambio("RUB")
        l.append("1 dólar = ₽ %s" % "{:,.2f}".format(usd / rub))
        l.append("")
        l.append("Se actualiza solo cada 6 horas. Para fijarlo a mano: <code>/tc 3.38</code> · "
                 "<code>/tc rub 0.0428</code>. Para volver a automático: <code>/tc auto</code>")
        return "\n".join(l)

    def _tc(self, chat, arg: str) -> None:
        if not arg:
            self.decir(chat, self._texto_tc())
            return
        n = C.normal(arg)
        if n.strip() in ("auto", "automatico", "hoy", "dia"):
            F.tc_a_automatico()
            self.decir(chat, "🔄 Listo, vuelve a ser automático.\n\n" + self._texto_tc())
            return
        moneda = "EUR" if "eur" in n else "RUB" if ("rub" in n or "rublo" in n) else "USD"
        m = re.search(r"\d*[.,]?\d+", arg)
        if not m:
            self.decir(chat, "Ejemplo: <code>/tc 3.72</code>")
            return
        valor = float(m.group(0).replace(",", "."))
        rango = (0.001, 1.0) if moneda == "RUB" else (0.1, 20.0)
        if not rango[0] < valor < rango[1]:
            self.decir(chat, "Ese tipo de cambio no parece real para %s (%s)." % (moneda, esc(valor)))
            return
        F.fijar_tipo_de_cambio(moneda, valor)
        self.decir(chat, "💱 Listo: 1 %s = S/ %s, fijo desde ahora (ya no se actualiza solo; "
                         "para volver a automático: <code>/tc auto</code>). Lo anotado antes no cambia." % (moneda, valor))

    def _ultimos(self, chat) -> None:
        filas = F.ultimos(self.notion, self.bases, 10)
        if not filas:
            self.decir(chat, "Aún no anotaste nada. Prueba: <code>45 almuerzo</code>")
            return
        l = ["🧾 <b>Últimos movimientos</b>", ""]
        botones = []
        for i, f in enumerate(filas, 1):
            tipo = f.get("Tipo") or "Gasto"
            fecha = (f.get("Fecha") or "")[:10]
            l.append("<b>%d.</b> %s %s%s · %s <i>%s</i>" % (
                i, C.emoji(tipo, f.get("Categoría") or ""), "+" if tipo == "Ingreso" else "",
                F.s(f.get("Monto S/")), esc(f.get("Descripción") or ""), "/".join(reversed(fecha[5:].split("-")))))
            botones.append((str(i), "mv:" + _pid(f["_id"])))
        l += ["", "<i>Toca el número del que quieras corregir o borrar.</i>"]
        self.decir(chat, "\n".join(l), [botones[:5], botones[5:]])

    # ---- corregir o borrar un movimiento ya anotado (no solo el ultimo)
    def _ver_movimiento(self, chat, pid: str) -> None:
        mov = F.movimiento(self.notion, self.bases, pid)
        if not mov:
            self.decir(chat, "Ese movimiento ya no está. Mira /ultimos otra vez.")
            return
        l = ["%s <b>%s</b> · %s" % (C.emoji(mov["tipo"], mov["categoria"]), esc(mov["tipo"]), esc(mov["categoria"])),
             "%s%s" % (self._en(mov["monto"], mov["moneda"]),
                       "" if mov["moneda"] == "PEN" else " = " + F.s(mov["monto_s"])),
             esc(mov["descripcion"])]
        extra = [x for x in (mov["medio"], (mov["tarjeta"] or "").lower() or None,
                             "%d cuotas" % mov["cuotas"] if mov.get("cuotas") else None,
                             "/".join(reversed(mov["fecha"].split("-")))) if x]
        l.append("<i>%s</i>" % esc(" · ".join(extra)))
        ti = C.TIPOS.index(mov["tipo"]) if mov["tipo"] in C.TIPOS else 0
        self.decir(chat, "\n".join(l),
                   [[("✏️ Cambiar monto", "me:" + pid), ("🏷 Cambiar categoría", "k:%s:%d" % (pid, ti))],
                    [("🗑 Borrar", "mb:" + pid)]])

    def _pedir_monto(self, chat, pid: str) -> None:
        mov = F.movimiento(self.notion, self.bases, pid)
        if not mov:
            self.decir(chat, "Ese movimiento ya no está. Mira /ultimos otra vez.")
            return
        self._corrigiendo[chat] = pid
        self.decir(chat, "✏️ <b>%s</b> está anotado en %s.\nEscribe el monto correcto, por ejemplo "
                         "<code>45</code> · <code>20 usd</code>." % (esc(mov["descripcion"]),
                                                                    self._en(mov["monto"], mov["moneda"])),
                   [[("✖️ Cancelar", "mn:no")]])

    def _cambiar_monto(self, chat, texto: str) -> None:
        pid = self._corrigiendo[chat]
        try:
            monto, moneda = _monto_y_moneda(texto)
        except ValueError:
            self.decir(chat, "Escribe solo el monto, por ejemplo <code>45</code> o <code>20 usd</code>.",
                       [[("✖️ Cancelar", "mn:no")]])
            return
        self._corrigiendo.pop(chat, None)
        viejo = F.movimiento(self.notion, self.bases, pid)
        if not viejo:
            self.decir(chat, "Ese movimiento ya no está. Mira /ultimos otra vez.")
            return
        l = self._quitar_efectos(viejo, pid)
        nuevo = dict(viejo, monto=monto, moneda=moneda or viejo["moneda"])
        F.corregir_monto(self.notion, pid, nuevo["monto"], nuevo["moneda"])
        l = [x for x in l if "vuelve a" not in x] + self._poner_efectos(nuevo, pid)
        self.decir(chat, "\n".join(["✏️ <b>%s</b>: %s → <b>%s</b>" % (
            esc(nuevo["descripcion"]), self._en(viejo["monto"], viejo["moneda"]),
            self._en(nuevo["monto"], nuevo["moneda"]))] + l))

    def _quitar_efectos(self, mov: dict, pid: str) -> list:
        """Deshace lo que un movimiento le hizo al banco y a la tarjeta. Si se anotó en esta corrida
        usa lo que quedó en memoria; si es viejo lo reconstruye con el medio de pago de la fila."""
        l = []
        if pid in self._cuenta_de:
            cuenta_id, delta = self._cuenta_de.pop(pid)
            c = next((x for x in F.cuentas(self.notion, self.bases) if _pid(x["id"]) == _pid(cuenta_id)), None)
        elif F.mueve_cuenta(mov) and PATRIMONIO in self.bases:
            c, delta = F.buscar_cuenta(self.notion, self.bases, mov["medio"], mov["moneda"]), F.delta_cuenta(mov)
        else:
            c = None
        if c:
            l.append("🏦 %s vuelve a %s" % (esc(c["nombre"]),
                                            F.s3(F.soles(F.mover_cuenta(self.notion, c, -delta), c["moneda"]))))
        if pid in self._credito_de:
            deuda_id, cargo = self._credito_de.pop(pid)
            d = next((x for x in F.deudas(self.notion, self.bases, todas=True) if _pid(x["id"]) == _pid(deuda_id)), None)
            moneda = None
        elif F.va_a_tarjeta(mov) and DEUDAS in self.bases:
            d, cargo, moneda = F.deuda_de_tarjeta(self.notion, self.bases, mov["medio"]), mov["monto"], mov["moneda"]
        else:
            d = None
        if d:
            l.append("💳 %s vuelve a %s" % (esc(d["deuda"]),
                                            F.s3(F.soles(F.pagar_deuda(self.notion, d, cargo, moneda), d["moneda"]))))
        if pid in self._metas_de:
            meta, monto = self._metas_de.pop(pid)
            actual = F.buscar_meta(F.metas(self.notion, self.bases), meta["meta"]) or meta
            l.append("🎯 %s vuelve a %s" % (esc(meta["meta"]), F.s(F.sumar_a_meta(self.notion, actual, -monto))))
        elif mov["tipo"] == "Ahorro" and METAS in self.bases:
            l.append("<i>Si ese ahorro iba a una meta, bájalo a mano en Notion: no queda anotado a cuál.</i>")
        return l

    def _poner_efectos(self, mov: dict, pid: str) -> list:
        """Vuelve a aplicar el movimiento al banco y a la tarjeta (después de corregirle el monto)."""
        l = []
        if F.va_a_tarjeta(mov) and DEUDAS in self.bases:
            d = F.cargar_a_tarjeta(self.notion, self.bases, mov["medio"], mov["monto"], mov["moneda"])
            self._credito_de[pid] = (d["id"], d["cargo"])
            l.append("💳 %s: ahora debes %s" % (esc(d["deuda"]), F.s3(F.soles(d["saldo"], d["moneda"]))))
        if F.mueve_cuenta(mov) and PATRIMONIO in self.bases:
            c = F.buscar_cuenta(self.notion, self.bases, mov["medio"], mov["moneda"])
            if c:
                delta = F.delta_cuenta(mov)
                self._cuenta_de[pid] = (c["id"], delta)
                l.append("🏦 %s ahora tiene %s" % (esc(c["nombre"]),
                                                   F.s3(F.soles(F.mover_cuenta(self.notion, c, delta), c["moneda"]))))
        return l

    # ---- bucle
    def _refrescar_tc(self) -> None:
        """Baja el tipo de cambio del dia en el rato libre, no cuando alguien espera respuesta.

        Si la fuente cuelga en vez de fallar, los segundos de espera los pone este rato
        muerto entre mensaje y mensaje; antes los ponia el usuario, que veia el bot mudo.
        """
        try:
            F.tc_automatico()
        except Exception as exc:          # nunca puede tumbar el bucle
            print("  [bot] no pude bajar el tipo de cambio: %s: %s" % (type(exc).__name__, exc))

    def correr(self, una_vez: bool = False) -> int:
        offset = leer_offset()
        fallos = 0
        if not una_vez:
            self._refrescar_tc()          # al arrancar, para que el primer mensaje no espere
        while True:
            try:
                updates = self.tg.updates(offset, timeout=0 if una_vez else 30)
                fallos = 0
            except TelegramError as exc:
                if exc.code in (401, 409):
                    return codigo_salida(exc)
                fallos += 1
                espera = min(60, 10 * fallos)
                print("  [telegram] %s; reintento en %d s" % (exc, espera))
                time.sleep(espera)
                continue
            for u in updates:
                offset = u["update_id"] + 1
                try:
                    guardar_offset(offset)
                except OSError as exc:
                    print("  [bot] no pude guardar el offset: %s" % exc)
                try:
                    self.procesar(u)
                except Exception as exc:  # un update roto no puede tumbar el bot
                    print("  [bot] error procesando update %s: %s: %s" % (u.get("update_id"), type(exc).__name__, exc))
            if una_vez:
                return 0
            self._refrescar_tc()          # ya se contesto todo: ahora si, el rato libre


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--una-vez", action="store_true")
    args = ap.parse_args()
    bases = cargar_bases()
    faltan = [b for b in (MOVIMIENTOS, PRESUPUESTO, PATRIMONIO, METAS) if b not in bases]
    if faltan:
        print("Faltan bases en data/bases.json (%s). Corre primero: python3 setup_notion.py" % ", ".join(faltan))
        return 1
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        (DATA / ".escritura").write_text("ok")
    except OSError as exc:
        print("No puedo escribir en %s: %s" % (DATA, exc))
        return 1
    try:
        tg = Telegram()
        notion = Notion()
    except (TelegramError, NotionError) as exc:
        print(exc)
        return 1
    if not TELEGRAM_USUARIOS:
        print("Aviso: TELEGRAM_USUARIOS esta vacio; el bot solo dira su ID a quien escriba.")
    try:
        with turno_del_bot():
            yo = tg.yo()
            print("Bot @%s escuchando. Ctrl+C para salir." % yo.get("username"), flush=True)
            return Bot(tg, notion, bases, TELEGRAM_USUARIOS).correr(args.una_vez)
    except TelegramError as exc:
        return codigo_salida(exc)
    except KeyboardInterrupt:
        print("\nChau.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
