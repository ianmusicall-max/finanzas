"""Reloj de trabajo: cronometra una tarea y avisa cuando llega al tope.

Nacio para medir cuanto toman las publicaciones de Facebook y no pasarse de hora (21/10/2026).
Cada bloque terminado se guarda, asi que a la segunda vez el bot ya puede decir cuanto suele
tomar: eso es lo que convierte el cronometro en algo util y no en un reloj mas.

**No hace falta ningun timer nuevo en el servidor.** El bot ya esta despierto escuchando Telegram
(`getUpdates` con espera de 30 s), asi que en cada vuelta del bucle pregunta `vencidos()` y manda
el aviso que toque. Por eso la alarma puede llegar con hasta ~30 s de atraso, que para bloques de
media hora no se nota.

El estado va a disco porque `finanzas-autoupdate` reinicia el bot cada vez que hay algo nuevo en
main: un bloque a medio correr no puede morir con el reinicio (la misma leccion que los
formularios, 09/10/2026).
"""

import json
import re
from datetime import datetime, timedelta
from typing import Optional

from config import DATA, ahora
from idiomas import t

ESTADO = DATA / "reloj.json"

AVISOS = 2          # al llegar al tope y una vez mas; despues se calla para no ser un martillo
RECORDAR = 0.5      # el segundo aviso al 50% pasado el tope
GUARDA = 200        # cuantos bloques terminados se guardan por tarea


def _clave(tarea: str) -> str:
    return " ".join(tarea.strip().lower().split())


def _leer() -> dict:
    """El archivo, con todas las claves puestas. Un archivo roto o a medias no puede tumbar el bot,
    asi que cualquier cosa que no tenga la forma esperada se reemplaza por lo vacio."""
    try:
        d = json.loads(ESTADO.read_text())
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    for clave, vacio in (("corriendo", {}), ("hechos", []), ("pendiente", {})):
        if not isinstance(d.get(clave), type(vacio)):
            d[clave] = vacio
    return d


def _escribir(d: dict) -> None:
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        ESTADO.write_text(json.dumps(d, ensure_ascii=False))
    except OSError:
        pass   # si no se puede escribir, el bot sigue andando con lo que tiene


def _minutos(desde: str, hasta: Optional[datetime] = None) -> float:
    d = datetime.fromisoformat(desde)
    return max(0.0, ((hasta or ahora()) - d).total_seconds() / 60.0)


def reloj(minutos: float) -> str:
    """45.2 -> '45 min'. 95 -> '1 h 35 min'."""
    m = int(round(minutos))
    if m < 60:
        return t("%d min") % m
    return t("%d h %02d min") % divmod(m, 60)


# ---------------------------------------------------------------- empezar, ver, terminar

def iniciar(chat, tarea: str, tope: Optional[int] = None) -> str:
    d = _leer()
    corriendo = d["corriendo"].get(str(chat))
    if corriendo:
        return (t("⏱ Ya tienes <b>%s</b> corriendo, van %s.\nCiérralo con /reloj fin o déjalo con "
                  "/reloj corta.") % (corriendo["tarea"], reloj(_minutos(corriendo["desde"]))))
    if not tarea:
        return t("¿Qué estás haciendo? Por ejemplo: <code>/reloj facebook 45</code>")
    d["corriendo"][str(chat)] = {"tarea": tarea.strip(), "desde": ahora().isoformat(),
                                 "tope": int(tope) if tope else None, "avisos": 0}
    _escribir(d)
    h = _historial(d, tarea)
    extra = ""
    if tope:
        extra = t("\nTe aviso a los %d min.") % tope
    elif h["veces"]:
        extra = t("\nLa última vez te tomó %s.") % reloj(h["ultimo"])
    if h["veces"]:
        extra += t("\nPromedio de <b>%s</b>: %s (%d veces).") % (tarea.strip(), reloj(h["promedio"]), h["veces"])
    return t("▶️ <b>%s</b>, arrancando.%s") % (tarea.strip(), extra)


def estado(chat) -> str:
    d = _leer()
    c = d["corriendo"].get(str(chat))
    if not c:
        return t("No tienes nada corriendo. Arranca con <code>/reloj facebook 45</code>.")
    van = _minutos(c["desde"])
    txt = t("⏱ <b>%s</b>: van %s.") % (c["tarea"], reloj(van))
    if c["tope"]:
        falta = c["tope"] - van
        txt += (t("\nTe pasaste por %s del tope de %d min.") % (reloj(-falta), c["tope"])) if falta < 0 \
            else (t("\nQuedan %s de los %d min.") % (reloj(falta), c["tope"]))
    return txt


def terminar(chat) -> str:
    d = _leer()
    c = d["corriendo"].pop(str(chat), None)
    if not c:
        return t("No tenías nada corriendo.")
    van = _minutos(c["desde"])
    d["hechos"].append({"tarea": c["tarea"], "minutos": round(van, 1), "fecha": ahora().date().isoformat()})
    mismos = [h for h in d["hechos"] if _clave(h["tarea"]) == _clave(c["tarea"])]
    if len(mismos) > GUARDA:
        sobran = {id(h) for h in mismos[:-GUARDA]}
        d["hechos"] = [h for h in d["hechos"] if id(h) not in sobran]
    _escribir(d)
    h = _historial(d, c["tarea"])
    txt = t("⏹ <b>%s</b>: %s.") % (c["tarea"], reloj(van))
    if c["tope"]:
        txt += t(" Te pasaste %s del tope.") % reloj(van - c["tope"]) if van > c["tope"] + 0.5 \
            else t(" Dentro del tope de %d min. 👏") % c["tope"]
    if h["veces"] > 1:
        txt += t("\n\nPromedio: <b>%s</b> · mejor %s · peor %s (%d veces).") % (
            reloj(h["promedio"]), reloj(h["minimo"]), reloj(h["maximo"]), h["veces"])
    return txt


def cortar(chat) -> str:
    d = _leer()
    c = d["corriendo"].pop(str(chat), None)
    if not c:
        return t("No tenías nada corriendo.")
    _escribir(d)
    return t("✖️ <b>%s</b> cortado, no se guardó (iban %s).") % (c["tarea"], reloj(_minutos(c["desde"])))


# ------------------------------------------------- los botones: primero el tope, despues el nombre
# Se toca "30 min" y el bot pregunta que vas a hacer. Ese "te estoy preguntando el nombre" tambien
# tiene que vivir en disco: si el bot se reinicia justo ahi, lo que escribas despues no se puede
# perder ni, peor, anotarse como un gasto.

def corriendo(chat) -> bool:
    return str(chat) in _leer()["corriendo"]


TOPE_MAX = 24 * 60     # mas de un dia no es un bloque de trabajo, es un error de tecleo


def pedir_nombre(chat, tope: int) -> None:
    """Ya se eligio el tope (o se eligio 'sin tope'): falta saber que va a hacer."""
    d = _leer()
    d["pendiente"][str(chat)] = {"tope": int(tope), "paso": "nombre", "dia": ahora().date().isoformat()}
    _escribir(d)


def pedir_tope(chat) -> None:
    """Toco "Otro": primero cuantos minutos, despues el nombre."""
    d = _leer()
    d["pendiente"][str(chat)] = {"tope": None, "paso": "tope", "dia": ahora().date().isoformat()}
    _escribir(d)


def esperando(chat) -> bool:
    """Si quedo preguntando el nombre. Lo de otro dia se descarta: no revive al dia siguiente."""
    p = _leer()["pendiente"].get(str(chat))
    return bool(p) and p.get("dia") == ahora().date().isoformat()


def olvidar(chat) -> str:
    d = _leer()
    habia = d["pendiente"].pop(str(chat), None)
    if habia is not None:
        _escribir(d)
    return t("👌 Listo, no arranco nada.")


def con_texto(chat, texto: str) -> str:
    """Lo que escribio mientras se le preguntaba algo: los minutos o el nombre de la tarea."""
    d = _leer()
    p = d["pendiente"].get(str(chat))
    if p is None:
        return t("Ese botón ya no sirve. Empieza otra vez con /reloj.")
    if p.get("paso") == "tope":
        minutos = _minutos_de(texto)
        if not minutos:
            return t("Escribe solo cuánto tiempo, por ejemplo <code>90</code> minutos, "
                     "<code>2 horas</code> o <code>1h30</code>.")
        p["tope"], p["paso"] = minutos, "nombre"
        _escribir(d)
        return t("⏱ %s. ✏️ ¿Y qué vas a hacer?") % reloj(minutos)
    d["pendiente"].pop(str(chat), None)
    _escribir(d)
    return iniciar(chat, texto[:60], p.get("tope") or None)


def _minutos_de(texto: str):
    """"90" -> 90 · "2 horas" -> 120 · "1h30" -> 90 · "1.5 h" -> 90. None si no se entiende."""
    t = " ".join(texto.strip().lower().replace(",", ".").split())
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hora|horas)\s*(\d{1,2})?\s*(?:m|min|minutos)?$", t)
    if m:
        total = float(m.group(1)) * 60 + (int(m.group(2)) if m.group(2) else 0)
    else:
        m = re.match(r"^(\d+(?:\.\d+)?)\s*(?:m|min|mins|minuto|minutos)?$", t)
        if not m:
            return None
        total = float(m.group(1))
    total = int(round(total))
    return total if 1 <= total <= TOPE_MAX else None


# ---------------------------------------------------------------- historial

def _historial(d: dict, tarea: str) -> dict:
    ms = [h["minutos"] for h in d["hechos"] if _clave(h["tarea"]) == _clave(tarea)]
    if not ms:
        return {"veces": 0, "promedio": 0.0, "minimo": 0.0, "maximo": 0.0, "ultimo": 0.0}
    return {"veces": len(ms), "promedio": sum(ms) / len(ms), "minimo": min(ms),
            "maximo": max(ms), "ultimo": ms[-1]}


def historial(tarea: str) -> dict:
    return _historial(_leer(), tarea)


def tareas() -> str:
    d = _leer()
    nombres = {}
    for h in d["hechos"]:
        nombres.setdefault(_clave(h["tarea"]), h["tarea"])
    if not nombres:
        return t("Todavía no has cronometrado nada. Arranca con <code>/reloj facebook 45</code>.")
    filas = []
    for clave, nombre in nombres.items():
        s = _historial(d, nombre)
        filas.append((s["promedio"] * s["veces"], t("• <b>%s</b> · %s de promedio · %d %s") % (
            nombre, reloj(s["promedio"]), s["veces"], t("vez") if s["veces"] == 1 else t("veces"))))
    filas.sort(reverse=True)
    return t("⏱ <b>Tu tiempo</b>\n\n%s") % "\n".join(x for _, x in filas)


# ---------------------------------------------------------------- lo que avisa el bot

def vencidos(hasta: Optional[datetime] = None) -> list:
    """(chat, texto) de los topes que vencieron. El bucle del bot la llama en cada vuelta."""
    d = _leer()
    hasta = hasta or ahora()
    avisos, cambio = [], False
    for chat, c in d["corriendo"].items():
        if not c.get("tope"):
            continue
        van = _minutos(c["desde"], hasta)
        hechos = int(c.get("avisos") or 0)
        if hechos == 0 and van >= c["tope"]:
            avisos.append((int(chat), t("⏰ <b>%s</b>: llegaste al tope de %d min.\n/reloj fin para cerrarlo.") % (
                c["tarea"], c["tope"])))
            c["avisos"], cambio = 1, True
        elif hechos == 1 and van >= c["tope"] * (1 + RECORDAR):
            avisos.append((int(chat), t("⏰ <b>%s</b>: vas %s, %s pasado del tope.\nNo te vuelvo a molestar.") % (
                c["tarea"], reloj(van), reloj(van - c["tope"]))))
            c["avisos"], cambio = AVISOS, True
    if cambio:
        _escribir(d)
    return avisos
