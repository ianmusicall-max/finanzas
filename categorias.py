"""Categorias, medios de pago y palabras clave para clasificar un movimiento solo.

Las categorias salen de la hoja "Finanzas Personales 2025". Cada categoria de
gasto tiene un grupo para la regla 50/30/20: necesidad, deseo o finanzas.
"""
import unicodedata

TIPOS = ["Gasto", "Ingreso", "Ahorro", "Inversión"]

# categoria -> (grupo 50/30/20, emoji, palabras clave)
GASTOS = {
    "Vivienda": ("Necesidad", "🏠", ["alquiler", "renta", "hipoteca", "departamento", "depa", "mantenimiento", "autovaluo", "arbitrios", "condominio"]),
    "Servicios del hogar": ("Necesidad", "💡", ["luz", "agua", "gas", "internet", "cable", "telefono", "celular", "plan", "enel", "sedapal", "calidda", "claro", "movistar", "entel", "bitel"]),
    "Alimentación": ("Necesidad", "🛒", ["mercado", "supermercado", "super", "plaza vea", "wong", "metro", "tottus", "vivanda", "makro", "bodega", "verduras", "fruta", "pan", "abarrotes"]),
    "Transporte": ("Necesidad", "🚕", ["taxi", "uber", "cabify", "didi", "indrive", "bus", "combi", "metropolitano", "gasolina", "combustible", "grifo", "peaje", "estacionamiento", "cochera", "pasaje"]),
    "Salud": ("Necesidad", "🩺", ["farmacia", "inkafarma", "mifarma", "medicina", "pastillas", "doctor", "clinica", "cita", "dentista", "analisis", "seguro medico", "eps"]),
    "Educación": ("Necesidad", "📚", ["matricula", "curso", "universidad", "colegio", "clase", "libro", "pension", "academia", "idioma"]),
    "Gastos financieros": ("Necesidad", "🏦", ["comision", "interes", "intereses", "desgravamen", "mantenimiento de cuenta", "itf", "cuota", "membresia tarjeta"]),
    "Comida y restaurantes": ("Deseo", "🍽", ["almuerzo", "cena", "desayuno", "restaurante", "menu", "pollo", "chifa", "ceviche", "pizza", "hamburguesa", "sushi", "rappi", "pedidosya", "delivery", "cafe", "starbucks", "lomo", "aji de gallina"]),
    "Chatarra y golosinas": ("Deseo", "🍫", ["golosina", "chocolate", "snack", "gaseosa", "helado", "dulce", "galleta", "papitas", "chatarra"]),
    "Bares y discotecas": ("Deseo", "🍻", ["bar", "discoteca", "cerveza", "trago", "chela", "pisco", "vino", "fiesta", "after"]),
    "Entretenimiento": ("Deseo", "🎬", ["cine", "concierto", "entrada", "teatro", "juego", "videojuego", "playstation", "steam", "evento", "tickets"]),
    "Suscripciones": ("Deseo", "📺", ["netflix", "spotify", "youtube", "disney", "hbo", "max", "prime", "icloud", "google one", "chatgpt", "claude", "suscripcion", "canva", "adobe"]),
    "Membresías": ("Deseo", "🏋", ["gimnasio", "gym", "smart fit", "membresia", "club"]),
    "Ropa y cuidado personal": ("Deseo", "👕", ["ropa", "zapatillas", "zapatos", "polo", "camisa", "pantalon", "corte", "peluqueria", "barberia", "perfume", "crema"]),
    "Accesorios y tecnología": ("Deseo", "💻", ["celular nuevo", "laptop", "audifonos", "cargador", "cable usb", "mouse", "teclado", "accesorio", "tecnologia", "gadget", "amazon", "aliexpress", "temu"]),
    "Viajes": ("Deseo", "✈️", ["vuelo", "pasaje aereo", "avianca", "latam", "sky", "hotel", "airbnb", "hostal", "viaje", "tour"]),
    "Regalos": ("Deseo", "🎁", ["regalo", "cumpleanos", "detalle", "flores"]),
    "Mascotas": ("Necesidad", "🐾", ["veterinario", "mascota", "perro", "gato", "comida de perro"]),
    "Negocio": ("Necesidad", "💼", ["anuncio", "publicidad", "ads", "facebook ads", "meta ads", "hosting", "dominio", "servidor", "api", "distribucion", "freshtunes", "ditto"]),
    "Otros": ("Deseo", "📦", []),
}

INGRESOS = {
    "Sueldo": ("💼", ["sueldo", "salario", "planilla", "quincena", "gratificacion", "cts"]),
    "Facebook": ("📘", ["facebook", "meta", "fb", "monetizacion", "estrellas", "reels"]),
    "Música y distribución": ("🎵", ["freshtunes", "ditto", "distrokid", "regalias", "royalties", "spotify pago", "agregadora"]),
    "Ventas": ("🛍", ["venta", "vendi", "cliente", "plantilla"]),
    "Criptomonedas": ("🪙", ["usdt", "binance", "cripto", "bitcoin", "btc", "earn"]),
    "Inversiones": ("📈", ["dividendo", "intereses ganados", "rendimiento", "plazo fijo", "fondo mutuo"]),
    "Otros ingresos": ("💰", []),
}

AHORROS = {
    "Fondo de emergencia": ("🛟", ["emergencia"]),
    "Metas": ("🎯", ["meta", "auto", "departamento", "viaje"]),
    "Ahorro general": ("🐷", []),
}

INVERSIONES = {
    "Fondos y acciones": ("📈", ["fondo", "accion", "acciones", "etf", "bolsa"]),
    "Cripto": ("🪙", ["usdt", "btc", "bitcoin", "cripto", "binance"]),
    "Inmueble": ("🏢", ["inmueble", "terreno", "departamento", "depa"]),
    "Negocio propio": ("💼", ["negocio", "emprendimiento", "equipo"]),
    "Otras inversiones": ("💹", []),
}

MEDIOS = ["Efectivo", "Yape", "Plin", "Interbank", "BCP", "BBVA", "Scotiabank", "Ripley", "CMR", "Oh",
          "PayPal", "Payoneer", "Binance"]

# Clases de patrimonio: (clase, tipo)
ACTIVOS = ["Efectivo y bancos", "Inversiones", "Cripto", "Inmueble", "Vehículo", "Por cobrar", "Otro activo"]
PASIVOS = ["Tarjeta de crédito", "Préstamo", "Hipoteca", "Por pagar", "Otra deuda"]
LIQUIDOS = {"Efectivo y bancos"}   # lo que cuenta para el fondo de emergencia

GRUPOS = ["Necesidad", "Deseo"]


def normal(texto: str) -> str:
    """minusculas y sin tildes, para comparar palabras."""
    t = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def por_tipo(tipo: str) -> dict:
    return {"Gasto": GASTOS, "Ingreso": INGRESOS, "Ahorro": AHORROS, "Inversión": INVERSIONES}[tipo]


def nombres(tipo: str) -> list:
    return list(por_tipo(tipo).keys())


def otros(tipo: str) -> str:
    return {"Gasto": "Otros", "Ingreso": "Otros ingresos", "Ahorro": "Ahorro general", "Inversión": "Otras inversiones"}[tipo]


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
    """Categoria por nombre escrito a mano ('comida' -> 'Comida y restaurantes')."""
    t = normal(texto).strip()
    if not t:
        return None
    for cat in nombres(tipo):
        if normal(cat) == t:
            return cat
    for cat in nombres(tipo):
        if normal(cat).startswith(t) or t in normal(cat).split():
            return cat
    return adivinar(tipo, texto)


def buscar_medio(texto: str):
    t = " %s " % normal(texto)
    for m in MEDIOS:
        if " %s " % normal(m) in t:
            return m
    return None
