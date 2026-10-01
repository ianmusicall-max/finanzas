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
from datetime import timedelta

import categorias as C
import finanzas as F
import informes as I
from config import DATA, TELEGRAM_USUARIOS
from notion import DEUDAS, METAS, MOVIMIENTOS, PATRIMONIO, PRESUPUESTO, Notion, NotionError, cargar_bases
from formularios import Formularios
from lector import MONEDAS, NoEntendi, _numero, interpretar
from telegram import Telegram, TelegramError, esc, guardar_offset, leer_offset, turno_del_bot

AYUDA = (
    "💰 <b>Finanzas</b> · todo queda en Notion\n\n"
    "<b>Anotar con formulario</b> (botones, como tus Google Forms):\n"
    "/gasto · /ingreso · /ahorro · /inversion\n\n"
    "<b>O rápido</b>, escribiendo como hablas:\n"
    "<code>45 almuerzo</code> · gasto\n"
    "<code>12.50 taxi yape ayer</code> · con medio de pago y fecha\n"
    "<code>120 zapatillas cmr credito</code> · a crédito: se suma a la deuda de la tarjeta\n"
    "<code>+3500 sueldo</code> · ingreso\n"
    "<code>+200 usd facebook</code> · ingreso en dólares\n"
    "<code>ahorro 500 emergencia</code> · suma a esa meta\n"
    "<code>inversion 1000 fondo mutuo</code>\n\n"
    "<b>Ver</b>\n"
    "/hoy · /ayer · /semana · /mes · resúmenes\n"
    "/presupuesto · cuánto llevas de cada categoría\n"
    "/patrimonio · lo que tienes menos lo que debes\n"
    "/metas · avance de tus metas de ahorro\n"
    "/deudas · cuánto debes y a quién\n"
    "/consejos · qué mejorar según tus números\n"
    "/metodos · formas de manejar tu dinero\n"
    "/ultimos · lo último que anotaste\n\n"
    "<b>Ajustar</b>\n"
    "<code>/presupuesto comida 800</code>\n"
    "<code>/activo Interbank 5200</code> · <code>/deuda Tarjeta Ripley 1200</code>\n"
    "<code>/pago Ripley 300</code> · baja el saldo de una deuda\n"
    "<code>/meta Auto 100000</code>\n"
    "<code>/tc 3.72</code> · <code>/tc rub 0.046</code> · tipo de cambio\n"
    "/deshacer · borra lo último que anotaste"
)

MENU = [[("➖ Gasto", "m:gasto"), ("➕ Ingreso", "m:ingreso"), ("🐷 Ahorro", "m:ahorro")],
        [("📅 Hoy", "m:hoy"), ("🗓 Semana", "m:semana"), ("📆 Mes", "m:mes")],
        [("🧾 Presupuesto", "m:presupuesto"), ("🏦 Patrimonio", "m:patrimonio"), ("🎯 Metas", "m:metas")],
        [("💳 Deudas", "m:deudas"), ("💡 Consejos", "m:consejos")]]

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
    ("Efectivo y bancos", ["banco", "efectivo", "cuenta", "ahorros", "interbank", "bcp", "bbva", "scotiabank", "yape", "paypal", "payoneer"]),
]
TIPOS_DEUDA = [
    ("Tarjeta de crédito", ["tarjeta", "ripley", "cmr", "oh", "visa", "mastercard", "amex"]),
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
        self.form = Formularios(metas=self._nombres_metas)

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
                self._comando(chat, texto)
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
        pag = F.guardar_movimiento(self.notion, self.bases, mov)
        pid = _pid(pag["id"])
        self._ultimo[chat] = pid
        l = ["%s <b>%s</b> · %s" % (C.emoji(mov.tipo, mov.categoria), esc(mov.tipo), esc(mov.categoria))]
        monto = F.s(F.soles(mov.monto, mov.moneda))
        if mov.moneda != "PEN":
            monto = "%s %s = %s (TC %s)" % (mov.moneda, "{:,.2f}".format(mov.monto), monto, F.tipo_de_cambio(mov.moneda))
        l.append("%s · %s" % (monto, esc(mov.descripcion)))
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
            debe = F.s(F.soles(d["saldo"], d["moneda"]))
            if d["moneda"] != "PEN":
                debe += " (%s %s)" % (d["moneda"], "{:,.2f}".format(d["saldo"]))
            l.append("🧾 A crédito: %s %s. Ahora debes %s." % (
                "creé la deuda" if d["nueva"] else "se sumó a", esc(d["deuda"]), debe))
        if meta:
            nuevo = F.sumar_a_meta(self.notion, meta, F.soles(mov.monto, mov.moneda))
            self._metas_de[pid] = (meta, F.soles(mov.monto, mov.moneda))
            avance = nuevo / meta["objetivo"] if meta["objetivo"] else None
            l.append("🎯 %s: %s de %s (%s)" % (esc(meta["meta"]), F.s(nuevo), F.s(meta["objetivo"]), F.pct(avance)))
        if mov.tipo == "Gasto":
            aviso = self._aviso_presupuesto(mov.categoria)
            if aviso:
                l.append(aviso)
        ti = C.TIPOS.index(mov.tipo)
        if not mov.adivinada:
            l.append("\n¿De qué categoría es?")
            self.decir(chat, "\n".join(l), self._botones_categoria(pid, ti) + [[("↩️ Deshacer", "x:" + pid)]])
            return
        self.decir(chat, "\n".join(l), [[("🏷 Cambiar categoría", "k:%s:%d" % (pid, ti)), ("↩️ Deshacer", "x:" + pid)]])

    def _aviso_presupuesto(self, categoria: str) -> str:
        """Si con este gasto la categoria pasa del 80% o del 100% del presupuesto del mes."""
        try:
            plan = F.presupuesto(self.notion, self.bases)
            if categoria not in plan:
                return ""
            m = F.mes()
            g = F.resumir(F.movimientos(self.notion, self.bases, m.desde, F.hoy()), m).por_categoria.get(categoria, 0)
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
            elif partes[0] == "m":
                self._comando(chat, "/" + partes[1])
            elif partes[0] == "k" and len(partes) == 3:
                self.decir(chat, "Elige la categoría:", self._botones_categoria(partes[1], int(partes[2])))
            elif partes[0] == "c" and len(partes) == 4:
                self.tg.quitar_botones(chat, message_id)
                tipo = C.TIPOS[int(partes[2])]
                cat = C.nombres(tipo)[int(partes[3])]
                F.cambiar_categoria(self.notion, partes[1], tipo, cat)
                aviso = self._aviso_presupuesto(cat) if tipo == "Gasto" else ""
                self.decir(chat, "🏷 Listo: %s %s%s" % (C.emoji(tipo, cat), esc(cat), "\n" + aviso if aviso else ""))
            elif partes[0] == "x" and len(partes) == 2:
                self.tg.quitar_botones(chat, message_id)
                self._deshacer(chat, partes[1])
        except (ValueError, IndexError):
            self.decir(chat, "Ese botón ya no sirve. Escribe /ayuda.")
        except NotionError as exc:
            self.decir(chat, "⚠️ Notion no respondió: %s" % esc(str(exc)[:200]))

    def _deshacer(self, chat, pid: str) -> None:
        self.notion.archivar(pid)
        if pid in self._metas_de:
            meta, monto = self._metas_de.pop(pid)
            actual = F.buscar_meta(F.metas(self.notion, self.bases), meta["meta"]) or meta
            F.sumar_a_meta(self.notion, actual, -monto)
        if pid in self._credito_de:
            deuda_id, cargo = self._credito_de.pop(pid)
            d = next((x for x in F.deudas(self.notion, self.bases, todas=True) if _pid(x["id"]) == _pid(deuda_id)), None)
            if d:
                F.pagar_deuda(self.notion, d, cargo)
        if self._ultimo.get(chat) == pid:
            self._ultimo.pop(chat, None)
        self.decir(chat, "↩️ Borrado. (Queda en la papelera de Notion por 30 días.)")

    # ---- comandos
    def _comando(self, chat, texto: str) -> None:
        partes = texto.split(maxsplit=1)
        cmd = C.normal(partes[0].split("@")[0])
        arg = partes[1].strip() if len(partes) > 1 else ""
        forzar = {"/gasto": "Gasto", "/ingreso": "Ingreso", "/ahorro": "Ahorro", "/inversion": "Inversión"}
        if cmd in ("/start", "/ayuda", "/help", "/menu"):
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
            self.decir(chat, I.texto_deudas(self.notion, self.bases))
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
        elif cmd in ("/metodos", "/opciones"):
            self.decir(chat, METODOS)
        elif cmd == "/tc":
            self._tc(chat, arg)
        elif cmd == "/ultimos":
            self._ultimos(chat)
        elif cmd == "/deshacer":
            pid = self._ultimo.get(chat)
            if not pid:
                self.decir(chat, "No hay nada reciente para deshacer. Mira /ultimos y bórralo en Notion.")
            else:
                self._deshacer(chat, pid)
        elif cmd == "/cancelar":
            if self.form.activo(chat):
                self._responder(chat, self.form.cancelar(chat))
            else:
                self.decir(chat, "No hay nada en curso. 🙂")
        else:
            self.decir(chat, "No conozco ese comando.", MENU)

    def _presupuesto(self, chat, arg: str) -> None:
        if not arg:
            self.decir(chat, I.texto_presupuesto(self.notion, self.bases))
            return
        m = re.match(r"(.+?)\s+(\d[\d.,]*)\s*$", arg)
        if not m:
            self.decir(chat, "Escribe la categoría y el monto mensual: <code>/presupuesto comida 800</code>")
            return
        cat = C.buscar_categoria("Gasto", m.group(1))
        if not cat:
            self.decir(chat, "No reconozco la categoría «%s». Las que hay:\n%s" % (
                esc(m.group(1)), esc(", ".join(C.nombres("Gasto")))))
            return
        monto = _numero(m.group(2))
        F.fijar_presupuesto(self.notion, self.bases, cat, monto)
        self.decir(chat, "🧾 Presupuesto de %s %s: %s al mes." % (C.emoji("Gasto", cat), esc(cat), F.s(monto)))

    def _patrimonio(self, chat, clase: str, arg: str) -> None:
        if not arg:
            ej = "/activo Interbank 5200 · /activo Binance 800 usd · /activo Auto 45000" if clase == "Activo" else "/deuda Tarjeta Ripley 1200 · /deuda Préstamo BCP 15000"
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
            "🟢" if clase == "Activo" else "🔻", esc(nombre), esc(tipo), F.s(ahora), cambio, F.s(net)))

    def _deuda(self, chat, arg: str) -> None:
        if not arg:
            self.decir(chat, "Escribe el nombre y lo que debes hoy: <code>/deuda Tarjeta Ripley 1200</code> · "
                             "<code>/deuda Préstamo BCP 15000</code> · <code>/deuda Juan 200 usd</code>")
            return
        try:
            nombre, saldo, moneda, tipo = leer_patrimonio("Pasivo", arg)
        except NoEntendi as exc:
            self.decir(chat, esc(str(exc).replace("/activo Interbank 5200", "/deuda Tarjeta Ripley 1200")))
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
                             esc(nombre), esc(tipo), F.s(ahora), cambio, F.s(total)))

    def _pago(self, chat, arg: str) -> None:
        lista = F.deudas(self.notion, self.bases)
        m = re.match(r"(.+?)\s+(\d[\d.,]*)(\s*k)?(?:\s+(\S+))?\s*$", arg)
        if not m:
            nombres = ", ".join(d["deuda"] for d in lista) or "aún no tienes deudas (usa /deuda)"
            self.decir(chat, "Escribe la deuda y cuánto pagaste: <code>/pago Ripley 300</code>\nTus deudas: %s" % esc(nombres))
            return
        d = F.buscar_deuda(lista, m.group(1))
        if not d:
            self.decir(chat, "No encuentro la deuda «%s». Mira /deudas." % esc(m.group(1)))
            return
        moneda = MONEDAS.get(C.normal(m.group(4) or ""), None)
        monto = _numero(m.group(2)) * (1000 if m.group(3) else 1)
        nuevo = F.pagar_deuda(self.notion, d, monto, moneda)
        if nuevo <= 0:
            self.decir(chat, "🎉 ¡%s pagada por completo! Ya no aparece en tus deudas." % esc(d["deuda"]))
            return
        extra = "" if d["moneda"] == "PEN" else " (%s %s)" % (d["moneda"], "{:,.2f}".format(nuevo))
        self.decir(chat, "✅ Pago a %s. Te queda: <b>%s</b>%s" % (esc(d["deuda"]), F.s(F.soles(nuevo, d["moneda"])), extra))

    def _meta(self, chat, arg: str) -> None:
        m = re.match(r"(.+?)\s+(\d[\d.,]*)(\s*k)?\s*$", arg)
        if not m:
            self.decir(chat, "Escribe el nombre y el objetivo: <code>/meta Fondo de emergencia 20000</code>")
            return
        objetivo = _numero(m.group(2)) * (1000 if m.group(3) else 1)
        F.fijar_meta(self.notion, self.bases, m.group(1).strip(), objetivo)
        self.decir(chat, "🎯 Meta «%s»: %s.\nCuando ahorres escribe <code>ahorro 500 %s</code>" % (
            esc(m.group(1).strip()), F.s(objetivo), esc(m.group(1).strip().split()[0].lower())))

    def _tc(self, chat, arg: str) -> None:
        if not arg:
            self.decir(chat, "💱 Tipo de cambio: USD %s · EUR %s · RUB %s\nPara cambiarlo: <code>/tc 3.72</code> · "
                             "<code>/tc eur 4.05</code> · <code>/tc rub 0.046</code>" % (
                F.tipo_de_cambio("USD"), F.tipo_de_cambio("EUR"), F.tipo_de_cambio("RUB")))
            return
        n = C.normal(arg)
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
        self.decir(chat, "💱 Listo: 1 %s = S/ %s desde ahora. Lo anotado antes no cambia." % (moneda, valor))

    def _ultimos(self, chat) -> None:
        filas = F.ultimos(self.notion, self.bases, 10)
        if not filas:
            self.decir(chat, "Aún no anotaste nada. Prueba: <code>45 almuerzo</code>")
            return
        l = ["🧾 <b>Últimos movimientos</b>", ""]
        for f in filas:
            tipo = f.get("Tipo") or "Gasto"
            fecha = (f.get("Fecha") or "")[:10]
            l.append("%s %s%s · %s <i>%s</i>" % (
                C.emoji(tipo, f.get("Categoría") or ""), "+" if tipo == "Ingreso" else "",
                F.s(f.get("Monto S/")), esc(f.get("Descripción") or ""), "/".join(reversed(fecha[5:].split("-")))))
        self.decir(chat, "\n".join(l))

    # ---- bucle
    def correr(self, una_vez: bool = False) -> int:
        offset = leer_offset()
        fallos = 0
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
