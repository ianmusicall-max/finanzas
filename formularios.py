"""Los formularios del bot: las mismas preguntas que tenian los Google Forms
"Gastos 2025" e "Ingresos 2025", una por mensaje, con botones.

    Gasto:   fecha, cuenta, medio de pago, credito o debito (solo si es tarjeta),
             categoria, moneda, descripcion, importe
    Ingreso: fecha, medio de pago, categoria, moneda, descripcion, importe
    Ahorro:  fecha, meta, medio de pago, moneda, importe
    Inversion: fecha, categoria, medio de pago, moneda, descripcion, importe

Al final muestra el resumen con Guardar, Corregir y Cancelar. Esta clase no
habla con Telegram ni con Notion: recibe lo que toco o escribio la persona y
devuelve que contestar. Guardar lo hace el bot.

Los botones llevan el paso en el callback ("f:medio:3"): un boton viejo de un
paso que ya paso no puede meter un dato en otra pregunta.
"""
import json
from datetime import date, timedelta
from typing import Optional

import categorias as C
from config import AJUSTES, DATA, hoy
from lector import FECHA, Movimiento, NoEntendi, _numero

# paso: (pregunta, tipo de respuesta)
PASOS = {
    "fecha": ("📅 ¿Qué fecha?", "fecha"),
    "cuenta": ("🗂 ¿A qué cuenta va?", "opciones"),
    "medio": ("💳 ¿Con qué pagaste?", "opciones"),
    "medio_in": ("🏦 ¿Dónde entró el dinero?", "opciones"),
    "tarjeta": ("💳 ¿Crédito o débito?\n<i>Si es crédito, se suma a la deuda de esa tarjeta.</i>", "opciones"),
    "categoria": ("🏷 ¿Qué categoría?", "opciones"),
    "meta": ("🎯 ¿Para qué meta es?", "opciones"),
    "moneda": ("💱 ¿En qué moneda?", "opciones"),
    "descripcion": ("📝 Escribe una descripción corta (por ejemplo: <i>almuerzo con Ana</i>).", "texto"),
    "importe": ("💰 ¿Cuánto fue? Escribe solo el número (por ejemplo: <code>45.50</code>).", "numero"),
}

FORMULARIOS = {
    "gasto": ("Gasto", ["fecha", "cuenta", "medio", "tarjeta", "categoria", "moneda", "descripcion", "importe"]),
    "ingreso": ("Ingreso", ["fecha", "medio_in", "categoria", "moneda", "descripcion", "importe"]),
    "ahorro": ("Ahorro", ["fecha", "meta", "medio", "moneda", "importe"]),
    "inversion": ("Inversión", ["fecha", "categoria", "medio", "moneda", "descripcion", "importe"]),
}
TITULOS = {"gasto": "➖ Nuevo gasto", "ingreso": "➕ Nuevo ingreso", "ahorro": "🐷 Nuevo ahorro",
           "inversion": "📈 Nueva inversión"}
TIPOS_TARJETA = ["Débito", "Crédito"]
ETIQUETAS = {"fecha": "Fecha", "cuenta": "Cuenta", "medio": "Medio de pago", "medio_in": "Medio de pago",
             "tarjeta": "Tarjeta",
             "categoria": "Categoría", "meta": "Meta", "moneda": "Moneda", "descripcion": "Descripción",
             "importe": "Importe"}
SIN_META = "Sin meta (ahorro general)"
CANCELAR = [("✖️ Cancelar", "f:no")]


# ---------------------------------------------------------------- recuerdos
# Lo ultimo que elegiste en cada pregunta sale primero la proxima vez.

def _recuerdos() -> dict:
    try:
        return json.loads(AJUSTES.read_text()).get("ultimos", {})
    except (OSError, ValueError, AttributeError):
        return {}


def _recordar(clave: str, valor: str) -> None:
    try:
        a = json.loads(AJUSTES.read_text())
    except (OSError, ValueError):
        a = {}
    a.setdefault("ultimos", {})[clave] = valor
    DATA.mkdir(parents=True, exist_ok=True)
    AJUSTES.write_text(json.dumps(a, indent=2, ensure_ascii=False))


def _fecha_texto(d: date) -> str:
    if d == hoy():
        return "hoy (%s)" % d.strftime("%d/%m")
    if d == hoy() - timedelta(days=1):
        return "ayer (%s)" % d.strftime("%d/%m")
    return d.strftime("%d/%m/%Y")


def _botones(pares: list, por_fila: int = 2) -> list:
    return [pares[i:i + por_fila] for i in range(0, len(pares), por_fila)]


class Formularios:
    def __init__(self, metas=None):
        """metas: funcion que devuelve los nombres de las metas de Notion (para el formulario de ahorro)."""
        self.estado = {}        # chat -> {"forma", "i", "datos", "corrigiendo"}
        self.metas = metas or (lambda: [])

    def activo(self, chat) -> bool:
        return chat in self.estado

    def cancelar(self, chat) -> list:
        self.estado.pop(chat, None)
        return [{"texto": "Cancelado. No se guardó nada."}]

    # ---------------------------------------------------------------- inicio
    def iniciar(self, chat, forma: str) -> list:
        self.estado[chat] = {"forma": forma, "i": 0, "datos": {}, "corrigiendo": False}
        return [{"texto": "<b>%s</b>" % TITULOS[forma]}] + self._preguntar(chat)

    def _aplica(self, chat, paso: str) -> bool:
        """Crédito o débito solo se pregunta si se pagó con un banco o tarjeta."""
        if paso == "tarjeta":
            return self.estado[chat]["datos"].get("medio") in C.TARJETAS
        return True

    def _pasos(self, chat) -> list:
        return [p for p in FORMULARIOS[self.estado[chat]["forma"]][1] if self._aplica(chat, p)]

    def _paso(self, chat) -> Optional[str]:
        e = self.estado[chat]
        pasos = FORMULARIOS[e["forma"]][1]
        while e["i"] < len(pasos) and not self._aplica(chat, pasos[e["i"]]):
            e["i"] += 1
        return pasos[e["i"]] if e["i"] < len(pasos) else None

    def opciones(self, chat, paso: str) -> list:
        forma = self.estado[chat]["forma"]
        tipo = FORMULARIOS[forma][0]
        if paso == "cuenta":
            lista = list(C.CUENTAS)
        elif paso in ("medio", "medio_in"):
            lista = list(C.MEDIOS)
        elif paso == "categoria":
            lista = C.nombres(tipo)
        elif paso == "moneda":
            lista = list(C.MONEDAS)
        elif paso == "tarjeta":
            lista = list(TIPOS_TARJETA)
        elif paso == "meta":
            lista = list(self.metas()) + [SIN_META]
        else:
            return []
        ultimo = _recuerdos().get("%s.%s" % (forma, paso))
        if ultimo in lista:
            lista.remove(ultimo)
            lista.insert(0, ultimo)
        return lista

    def _preguntar(self, chat) -> list:
        paso = self._paso(chat)
        if paso is None:
            return self._resumen(chat)
        pregunta, clase = PASOS[paso]
        if clase == "opciones":
            lista = self.opciones(chat, paso)
            tipo = FORMULARIOS[self.estado[chat]["forma"]][0]
            pares = []
            for k, o in enumerate(lista):
                etiqueta = o
                if paso == "categoria":
                    etiqueta = "%s %s" % (C.emoji(tipo, o), o)
                pares.append((etiqueta, "f:%s:%d" % (paso, k)))
            if paso == "tarjeta":
                pares = [("💳 " + o if o == "Débito" else "🧾 " + o, d) for (o, d) in pares]
            por_fila = 4 if paso == "moneda" else 3 if paso in ("cuenta", "medio", "medio_in") else 2
            return [{"texto": pregunta, "botones": _botones(pares, por_fila) + [CANCELAR]}]
        if clase == "fecha":
            d = hoy()
            return [{"texto": pregunta + "\n<i>O escribe la fecha: 15/09</i>", "botones": [
                [("Hoy %s" % d.strftime("%d/%m"), "f:fecha:0"), ("Ayer", "f:fecha:1"), ("Anteayer", "f:fecha:2")],
                CANCELAR]}]
        if clase == "texto":
            return [{"texto": pregunta, "botones": [[("Omitir", "f:descripcion:-")], CANCELAR]}]
        return [{"texto": pregunta, "botones": [CANCELAR]}]

    # ---------------------------------------------------------------- respuestas
    def boton(self, chat, data: str) -> list:
        """data viene sin el prefijo "f:"."""
        if chat not in self.estado:
            return [{"texto": "Ese formulario ya terminó. Empieza otro desde el menú."}]
        if data == "no":
            return self.cancelar(chat)
        if data == "fix":
            return self._menu_corregir(chat)
        if data.startswith("edit:"):
            e = self.estado[chat]
            pasos = FORMULARIOS[e["forma"]][1]
            campo = data[5:]
            if campo in pasos:
                e["i"] = pasos.index(campo)
                e["corrigiendo"] = True
                return self._preguntar(chat)
            return self._resumen(chat)
        paso, _, valor = data.partition(":")
        if paso != self._paso(chat):
            return [{"texto": "Ese botón era de una pregunta anterior."}] + self._preguntar(chat)
        e = self.estado[chat]
        if paso == "fecha":
            e["datos"]["fecha"] = hoy() - timedelta(days=int(valor))
        elif paso == "descripcion" and valor == "-":
            e["datos"]["descripcion"] = ""
        else:
            lista = self.opciones(chat, paso)
            try:
                elegido = lista[int(valor)]
            except (ValueError, IndexError):
                return self._preguntar(chat)
            e["datos"][paso] = elegido
            _recordar("%s.%s" % (e["forma"], paso), elegido)
        return self._avanzar(chat)

    def texto(self, chat, texto: str) -> list:
        paso = self._paso(chat)
        e = self.estado[chat]
        if paso is None:
            return [{"texto": "Toca Guardar, Corregir o Cancelar."}] + self._resumen(chat)
        clase = PASOS[paso][1]
        t = texto.strip()
        if clase == "fecha":
            m = FECHA.search(t)
            if not m:
                return [{"texto": "No entendí la fecha. Escríbela así: <code>15/09</code> o toca un botón."}]
            d, mes = int(m.group(1)), int(m.group(2))
            anio = int(m.group(3)) if m.group(3) else hoy().year
            anio += 2000 if anio < 100 else 0
            try:
                f = date(anio, mes, d)
            except ValueError:
                return [{"texto": "Esa fecha no existe. Prueba otra vez."}]
            if not m.group(3) and f > hoy():
                f = date(anio - 1, mes, d)
            e["datos"]["fecha"] = f
        elif clase == "numero":
            try:
                n = _numero(t.replace(" ", "").lstrip("S/$€₽").strip())
            except ValueError:
                return [{"texto": "Escribe solo el número, por ejemplo <code>45.50</code>."}]
            if n <= 0:
                return [{"texto": "El importe tiene que ser mayor que cero."}]
            e["datos"]["importe"] = round(n, 2)
        elif clase == "texto":
            e["datos"]["descripcion"] = t[:200]
        else:
            # pregunta de botones: se acepta escribir la opcion
            lista = self.opciones(chat, paso)
            hit = next((o for o in lista if C.normal(o) == C.normal(t)), None) or \
                next((o for o in lista if C.normal(t) and C.normal(t) in C.normal(o)), None)
            if not hit:
                return [{"texto": "Elige una de las opciones con los botones."}] + self._preguntar(chat)
            e["datos"][paso] = hit
        return self._avanzar(chat)

    def _avanzar(self, chat) -> list:
        e = self.estado[chat]
        pasos = FORMULARIOS[e["forma"]][1]
        if e["corrigiendo"] and pasos[e["i"]] == "medio" and "tarjeta" in pasos and self._aplica(chat, "tarjeta"):
            e["i"] = pasos.index("tarjeta")   # cambio a un banco: falta saber si es credito o debito
        elif e["corrigiendo"]:
            e["corrigiendo"] = False
            e["i"] = len(pasos)
        else:
            e["i"] += 1
        return self._preguntar(chat)

    # ---------------------------------------------------------------- final
    def _resumen(self, chat) -> list:
        e = self.estado[chat]
        d = e["datos"]
        tipo = FORMULARIOS[e["forma"]][0]
        l = ["<b>%s</b> · revisa antes de guardar" % TITULOS[e["forma"]], ""]
        for paso in self._pasos(chat):
            v = d.get(paso)
            if paso == "fecha":
                v = _fecha_texto(v)
            elif paso == "importe":
                v = "%s %s" % (d.get("moneda", ""), "{:,.2f}".format(v))
            elif paso == "categoria":
                v = "%s %s" % (C.emoji(tipo, v), v)
            elif paso == "descripcion" and not v:
                v = "—"
            l.append("%s: <b>%s</b>" % (ETIQUETAS[paso], v))
        return [{"texto": "\n".join(l), "botones": [[("✅ Guardar", "f:ok"), ("✏️ Corregir", "f:fix")], CANCELAR]}]

    def _menu_corregir(self, chat) -> list:
        e = self.estado[chat]
        pares = [(ETIQUETAS[p], "f:edit:" + p) for p in self._pasos(chat)]
        return [{"texto": "¿Qué quieres corregir?", "botones": _botones(pares, 3)}]

    def terminar(self, chat):
        """Saca el movimiento listo para guardar y cierra el formulario.
        Devuelve (Movimiento, nombre de la meta o None)."""
        e = self.estado.pop(chat)
        d = e["datos"]
        tipo = FORMULARIOS[e["forma"]][0]
        meta = d.get("meta")
        if e["forma"] == "ahorro":
            if meta and meta != SIN_META:
                categoria = "Fondo de emergencia" if "emergencia" in C.normal(meta) else "Metas"
            else:
                meta, categoria = None, "Ahorro general"
            descripcion = "Ahorro para %s" % meta if meta else "Ahorro"
        else:
            categoria = d["categoria"]
            descripcion = d.get("descripcion") or categoria
        mov = Movimiento(tipo=tipo, monto=d["importe"], moneda=d.get("moneda", "PEN"),
                         descripcion=descripcion[:1].upper() + descripcion[1:], categoria=categoria,
                         medio=d.get("medio") or d.get("medio_in"), fecha=d.get("fecha") or hoy(),
                         cuenta=d.get("cuenta"),
                         tarjeta=d.get("tarjeta") if d.get("medio") in C.TARJETAS and tipo == "Gasto" else None)
        return mov, meta

    def listo(self, chat) -> bool:
        return chat in self.estado and self._paso(chat) is None
