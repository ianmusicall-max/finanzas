"""Clasificar un movimiento solo: la logica, igual para todos los dueños del sistema.

Los datos personales (categorias, bancos, tarjetas, alias) **no viven aca**: estan en
`perfiles/<nombre>.py` y se eligen con `PERFIL` en el `.env`. Asi dos personas pueden compartir
este codigo y tener cada una sus propias categorias, sin que una copia se separe de la otra.

Se reexporta todo con `import *` a proposito: los diez modulos que hacen `import categorias as C`
siguen usando `C.GASTOS`, `C.MEDIOS`, etc., y no hubo que tocar ninguno.
"""
import importlib
import unicodedata
from typing import Optional

from config import PERFIL

_perfil = importlib.import_module("perfiles.%s" % PERFIL)
globals().update({k: v for k, v in vars(_perfil).items() if not k.startswith("_")})

# Estructura del sistema, igual para todos: el codigo usa estos valores como llaves y los
# guarda en Notion tal cual, asi que no son cosa de cada perfil.
TIPOS = ["Gasto", "Ingreso", "Ahorro", "Inversión"]
GRUPOS = ["Necesidad", "Deseo"]
CUENTAS = ["Gastos", "Salud", "Inversión", "Educación"]
ACTIVOS = ["Efectivo y bancos", "Inversiones", "Cripto", "Inmueble", "Vehículo", "Por cobrar", "Otro activo"]
PASIVOS = ["Tarjeta de crédito", "Préstamo", "Hipoteca", "Por pagar", "Otra deuda"]
LIQUIDOS = {"Efectivo y bancos"}   # lo que cuenta para el fondo de emergencia

def deuda_de_tarjeta(medio: str) -> str:
    """La deuda (fila de Deudas) donde se acumula lo comprado a credito con esa tarjeta."""
    return DEUDA_TARJETA.get(medio) or "Tarjeta " + medio


def normal(texto: str) -> str:
    """minusculas y sin tildes, para comparar palabras."""
    t = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def por_tipo(tipo: str) -> dict:
    return {"Gasto": GASTOS, "Ingreso": INGRESOS, "Ahorro": AHORROS, "Inversión": INVERSIONES}[tipo]


def nombres(tipo: str) -> list:
    return list(por_tipo(tipo).keys())


def ahorro_de_meta(meta: Optional[str]) -> str:
    """A que categoria va un ahorro: la reserva, una meta con nombre, o sin destino.

    Lo decidian `bot.py` y `formularios.py` con los nombres en espanol escritos a mano
    ("Fondo de emergencia" / "Metas" / "Ahorro general"), asi que en un perfil en ruso
    escribian en Notion una categoria que no existe. Ahora lo dice el perfil, y para
    reconocer la reserva se usan sus propias palabras clave de AHORROS.
    """
    if not meta:
        return otros("Ahorro")
    n = normal(meta)
    claves = list(AHORROS.get(AHORRO_EMERGENCIA, ("", []))[1]) + [AHORRO_EMERGENCIA]
    if any(normal(k) in n for k in claves if k):
        return AHORRO_EMERGENCIA
    return AHORRO_METAS


def otros(tipo: str) -> str:
    return OTROS[tipo]


def emoji(tipo: str, categoria: str) -> str:
    info = por_tipo(tipo).get(categoria)
    if not info:
        return "•"
    return info[1] if tipo == "Gasto" else info[0]


def grupo(categoria: str) -> str:
    return GASTOS.get(categoria, ("Deseo",))[0]


def palabras(tipo: str, categoria: str) -> list:
    info = por_tipo(tipo)[categoria]
    return info[2] if tipo == "Gasto" else info[1]


def adivinar(tipo: str, texto: str):
    """La categoria cuya palabra clave aparece en el texto (la mas larga gana:
    'comida de perro' le gana a 'comida'). None si ninguna coincide."""
    t = " %s " % normal(texto)
    mejor, largo = None, 0
    for cat in nombres(tipo):
        for p in palabras(tipo, cat):
            pn = normal(p)
            if (" %s " % pn in t or (len(pn) > 4 and pn in t)) and len(pn) > largo:
                mejor, largo = cat, len(pn)
    return mejor


def buscar_categoria(tipo: str, texto: str):
    """Categoria por nombre escrito a mano ('comida' -> 'Restaurantes y cafés')."""
    t = normal(texto).strip()
    if not t:
        return None
    for cat in nombres(tipo):
        if normal(cat) == t:
            return cat
    for viejo, ahora in RENOMBRADAS.items():       # el nombre de antes sigue sirviendo
        if normal(viejo) == t and ahora in nombres(tipo):
            return ahora
    for cat in nombres(tipo):
        if normal(cat).startswith(t) or t in normal(cat).split():
            return cat
    return adivinar(tipo, texto)


def buscar_medio(texto: str):
    t = " %s " % normal(texto)
    for alias, m in ALIAS_MEDIOS.items():
        if " %s " % alias in t:
            return m
    for m in MEDIOS:
        if " %s " % normal(m) in t:
            return m
    return None


def vigente(categoria: str) -> str:
    """El nombre de ahora de una categoria leida de Notion ('Chatarra y golosinas' -> 'Golosinas')."""
    if not categoria:
        return categoria
    c = categoria.strip()
    if c in RENOMBRADAS:
        return RENOMBRADAS[c]
    cn = normal(c)
    for viejo, nuevo in RENOMBRADAS.items():
        if normal(viejo) == cn:
            return nuevo
    return c


def anteriores(categoria: str) -> list:
    """Como se llamaba antes esa categoria, para encontrar sus filas viejas en Notion."""
    return [v for v, n in RENOMBRADAS.items() if n == categoria]
