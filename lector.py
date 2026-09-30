"""Lee un mensaje escrito como uno lo diria y lo convierte en un movimiento.

    45 almuerzo                 gasto de S/ 45, Comida y restaurantes
    12.50 taxi yape ayer        gasto, Transporte, pagado con Yape, fecha de ayer
    +1943 usd facebook          ingreso en dolares, categoria Facebook
    ahorro 500 emergencia       ahorro, Fondo de emergencia
    inversion 1000 fondo mutuo  inversion
    20$ netflix 15/09           gasto en dolares con fecha

Si no reconoce la categoria usa la de "otros" y el bot ofrece botones para cambiarla.
"""
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import categorias as C
from config import hoy

PREFIJOS = {
    "+": "Ingreso", "ingreso": "Ingreso", "ingresos": "Ingreso", "cobre": "Ingreso", "cobro": "Ingreso",
    "gane": "Ingreso", "recibi": "Ingreso",
    "-": "Gasto", "gasto": "Gasto", "gaste": "Gasto", "pague": "Gasto", "compre": "Gasto",
    "ahorro": "Ahorro", "ahorre": "Ahorro", "guarde": "Ahorro",
    "inversion": "Inversión", "inverti": "Inversión", "invertir": "Inversión",
}

MONEDAS = {"usd": "USD", "$": "USD", "dolar": "USD", "dolares": "USD", "us$": "USD",
           "eur": "EUR", "€": "EUR", "euro": "EUR", "euros": "EUR",
           "pen": "PEN", "s/": "PEN", "s/.": "PEN", "soles": "PEN", "sol": "PEN", "lucas": "PEN"}

# 1,234.50 · 1234,50 · 45 · .5 ; con moneda pegada antes o despues
NUM = re.compile(r"(?<![\w/])(?P<pre>s/\.?|us\$|\$|€)?\s?(?P<n>\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s?(?P<suf>usd|eur|pen|\$|€|k)?(?![\w/])", re.I)
FECHA = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?!\d)")


@dataclass
class Movimiento:
    tipo: str
    monto: float
    moneda: str = "PEN"
    descripcion: str = ""
    categoria: str = ""
    medio: Optional[str] = None
    fecha: date = field(default_factory=hoy)
    adivinada: bool = True   # False si la categoria cayo en "otros"


class NoEntendi(ValueError):
    pass


def _numero(texto: str) -> float:
    """'1,234.50' -> 1234.5 · '1.234,50' -> 1234.5 · '12,5' -> 12.5 · '1,500' -> 1500"""
    t = texto
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t:
        ent, _, dec = t.rpartition(",")
        t = ent.replace(",", "") + ("." + dec if len(dec) <= 2 else dec)
    elif t.count(".") > 1 or (t.count(".") == 1 and len(t.rpartition(".")[2]) == 3):
        t = t.replace(".", "")
    return float(t)


def _fecha(texto: str, base: date):
    """Devuelve (fecha, texto sin la fecha)."""
    n = C.normal(texto)
    if re.search(r"\banteayer\b", n):
        return base - timedelta(days=2), re.sub(r"(?i)\banteayer\b", " ", texto)
    if re.search(r"\bayer\b", n):
        return base - timedelta(days=1), re.sub(r"(?i)\bayer\b", " ", texto)
    m = FECHA.search(texto)
    if m:
        d, mes = int(m.group(1)), int(m.group(2))
        anio = int(m.group(3)) if m.group(3) else base.year
        if anio < 100:
            anio += 2000
        try:
            f = date(anio, mes, d)
        except ValueError:
            raise NoEntendi("La fecha %s no existe." % m.group(0))
        if not m.group(3) and f > base:
            f = date(anio - 1, mes, d)   # "28/12" escrito en enero es del año pasado
        return f, texto[:m.start()] + " " + texto[m.end():]
    return base, texto


def interpretar(texto: str, tipo: Optional[str] = None, base: Optional[date] = None) -> Movimiento:
    base = base or hoy()
    t = " ".join((texto or "").split())
    if not t:
        raise NoEntendi("Escribe el monto y en qué fue, por ejemplo: 45 almuerzo")

    # tipo por la primera palabra ('+', 'ahorro', 'gaste'...)
    if t.startswith("+") or t.startswith("-"):
        tipo = tipo or PREFIJOS[t[0]]
        t = t[1:].strip()
    else:
        primera = C.normal(t.split()[0])
        if primera in PREFIJOS:
            tipo = tipo or PREFIJOS[primera]
            t = t.split(" ", 1)[1] if " " in t else ""

    fecha, t = _fecha(t, base)

    m = NUM.search(t)
    if not m:
        raise NoEntendi("No encontré el monto. Escribe primero cuánto fue, por ejemplo: 45 almuerzo")
    monto = _numero(m.group("n"))
    suf = (m.group("suf") or "").lower()
    if suf == "k":
        monto *= 1000
        suf = ""
    if monto <= 0:
        raise NoEntendi("El monto tiene que ser mayor que cero.")
    moneda = MONEDAS.get((m.group("pre") or suf or "").lower().rstrip("."), None)
    resto = (t[:m.start()] + " " + t[m.end():]).split()

    # la moneda tambien puede venir como palabra suelta: "20 dolares netflix"
    limpio = []
    for w in resto:
        wn = C.normal(w).strip(".,")
        if wn in MONEDAS and moneda is None:
            moneda = MONEDAS[wn]
        elif wn in ("en", "de", "con", "por", "para") and not limpio:
            continue
        else:
            limpio.append(w)
    moneda = moneda or "PEN"
    desc = " ".join(limpio)

    medio = C.buscar_medio(desc)
    if medio:
        desc = re.sub(r"(?i)\s*\b(con|por|via|desde)?\s*%s\b" % re.escape(medio), " ", desc)
        desc = " ".join(desc.split())

    if not tipo:
        tipo = "Ingreso" if C.adivinar("Ingreso", desc) and not C.adivinar("Gasto", desc) and _suena_a_ingreso(desc) else "Gasto"
    cat = C.adivinar(tipo, desc)
    adivinada = cat is not None
    desc = desc.strip(" -,.") or (cat or tipo)
    return Movimiento(tipo=tipo, monto=round(monto, 2), moneda=moneda, descripcion=desc[:1].upper() + desc[1:],
                      categoria=cat or C.otros(tipo), medio=medio, fecha=fecha, adivinada=adivinada)


def _suena_a_ingreso(desc: str) -> bool:
    """Sin '+' solo se toma como ingreso lo que claramente lo es ('sueldo', 'pago de facebook')."""
    n = C.normal(desc)
    return bool(re.search(r"\b(sueldo|salario|quincena|gratificacion|cts|pago de|me pagaron|cobre|regalias|dividendo)\b", n))
