"""Categorias, medios de pago y palabras clave para clasificar un movimiento solo.

Las categorias salen de la hoja "Finanzas Personales 2025". Cada categoria de
gasto tiene un grupo para la regla 50/30/20: necesidad, deseo o finanzas.
"""
import unicodedata

TIPOS = ["Gasto", "Ingreso", "Ahorro", "Inversión"]

# Las categorias del formulario "Gastos 2025", en el orden en que mas se usaron.
# categoria -> (grupo 50/30/20, emoji, palabras clave para el modo rapido)
GASTOS = {
    "Comida y restaurantes": ("Deseo", "🍽", ["almuerzo", "cena", "desayuno", "restaurante", "menu", "pollo", "chifa", "ceviche", "pizza", "hamburguesa", "sushi", "rappi", "pedidosya", "delivery", "cafe", "starbucks", "lomo", "aji de gallina", "shawarma"]),
    "Supermercado": ("Necesidad", "🛒", ["mercado", "supermercado", "super", "plaza vea", "wong", "metro", "tottus", "vivanda", "makro", "bodega", "verduras", "fruta", "pan", "abarrotes", "pyaterochka", "perekrestok", "magnit", "lenta", "vkusvill"]),
    "Chatarra y golosinas": ("Deseo", "🍫", ["golosina", "chocolate", "snack", "gaseosa", "helado", "dulce", "galleta", "papitas", "chatarra"]),
    "Movilidad": ("Necesidad", "🚕", ["taxi", "uber", "cabify", "didi", "indrive", "yandex", "bus", "combi", "metropolitano", "metro de", "pasaje", "peaje", "estacionamiento", "cochera", "tren"]),
    "Viajes": ("Deseo", "✈️", ["vuelo", "pasaje aereo", "avianca", "latam", "sky", "aeroflot", "pegasus", "hotel", "airbnb", "hostal", "viaje", "tour"]),
    "Comisiones Banco": ("Necesidad", "🏧", ["comision", "itf", "mantenimiento de cuenta", "transferencia"]),
    "Entretenimiento": ("Deseo", "🎬", ["cine", "concierto", "entrada", "teatro", "juego", "videojuego", "playstation", "steam", "evento", "tickets"]),
    "Accesorios y tecnología": ("Deseo", "💻", ["celular nuevo", "laptop", "audifonos", "cargador", "cable usb", "mouse", "teclado", "accesorio", "tecnologia", "gadget", "amazon", "aliexpress", "temu", "ozon", "wildberries"]),
    "Ropa y calzado": ("Deseo", "👕", ["ropa", "zapatillas", "zapatos", "polo", "camisa", "pantalon", "casaca", "medias"]),
    "Cuidado Personal": ("Deseo", "🧴", ["corte", "peluqueria", "barberia", "perfume", "crema", "shampoo", "desodorante"]),
    "Vivienda": ("Necesidad", "🏠", ["alquiler", "renta", "hipoteca", "departamento", "depa", "autovaluo", "arbitrios", "condominio"]),
    "Gastos financieros": ("Necesidad", "🏦", ["interes", "intereses", "desgravamen", "cuota", "membresia tarjeta", "seguro"]),
    "Suscripciones": ("Deseo", "📺", ["netflix", "spotify", "youtube", "disney", "hbo", "max", "prime", "icloud", "google one", "chatgpt", "claude", "suscripcion", "canva", "adobe", "terabox", "vpn", "adguard", "lightroom", "logic"]),
    "Padres": ("Necesidad", "👪", ["papa", "mama", "padres", "papas"]),
    "Hogar y decoración": ("Deseo", "🛋", ["mueble", "decoracion", "cocina", "sabanas", "toallas", "hogar"]),
    "Salud y Bienestar": ("Necesidad", "🧘", ["gimnasio", "gym", "yoga", "vitaminas", "suplementos", "proteina"]),
    "Medicina": ("Necesidad", "💊", ["farmacia", "inkafarma", "mifarma", "medicina", "pastillas", "remedio"]),
    "Servicios Rusia": ("Necesidad", "🇷🇺", ["zhkh", "kvartplata", "mts", "beeline", "megafon"]),
    "Cursos y aprendizaje": ("Necesidad", "📚", ["curso", "clase", "libro", "academia", "idioma", "udemy"]),
    "Servicios": ("Necesidad", "💡", ["luz", "agua", "gas", "internet", "cable", "telefono", "celular", "plan", "enel", "sedapal", "calidda", "claro", "movistar", "entel", "bitel"]),
    "Citas médicas": ("Necesidad", "🩺", ["doctor", "clinica", "cita", "dentista", "analisis", "consulta"]),
    "Combustible": ("Necesidad", "⛽", ["gasolina", "combustible", "grifo", "diesel"]),
    "Bares y discotecas": ("Deseo", "🍻", ["bar", "discoteca", "cerveza", "trago", "chela", "pisco", "vino", "fiesta", "after"]),
    "Universidad": ("Necesidad", "🎓", ["universidad", "matricula", "pension", "maestria"]),
    "Perros": ("Necesidad", "🐶", ["veterinario", "perro", "perros", "comida de perro", "mascota"]),
    "Otros": ("Deseo", "📦", []),
}

# Las del formulario "Ingresos 2025".
INGRESOS = {
    "Facebook": ("📘", ["facebook", "meta", "fb", "monetizacion", "estrellas", "reels"]),
    "Freshtunes": ("🎵", ["freshtunes"]),
    "Routenote": ("🎶", ["routenote"]),
    "Criptomonedas": ("🪙", ["usdt", "binance", "cripto", "bitcoin", "btc", "earn", "kucoin"]),
    "Ventas": ("🛍", ["venta", "vendi", "cliente", "plantilla"]),
    "Sueldo": ("💼", ["sueldo", "salario", "planilla", "quincena", "gratificacion", "cts"]),
    "Retiro de ahorro": ("🐷", ["retiro de ahorro", "saque del ahorro"]),
    "Otros ingresos": ("💰", []),
}

AHORROS = {
    "Fondo de emergencia": ("🛟", ["emergencia"]),
    "Metas": ("🎯", ["meta", "auto", "departamento", "viaje"]),
    "Ahorro general": ("🐷", []),
}

INVERSIONES = {
    "Inmueble": ("🏢", ["inmueble", "terreno", "departamento", "depa", "autovaluo", "abogado"]),
    "Fondos y acciones": ("📈", ["fondo", "accion", "acciones", "etf", "bolsa"]),
    "Cripto": ("🪙", ["usdt", "btc", "bitcoin", "cripto", "binance"]),
    "Negocio propio": ("💼", ["negocio", "emprendimiento", "equipo"]),
    "Otras inversiones": ("💹", []),
}

# Las cuentas del formulario de gastos: a que bolsillo se carga el gasto.
CUENTAS = ["Gastos", "Salud", "Inversión", "Educación", "Export Latam", "Facebook"]
MONEDAS = ["PEN", "RUB", "USD", "EUR"]

# Gastos que se pagan una vez al mes y no cuentan para el limite del dia a dia (/limite).
CATEGORIAS_FIJAS = {"Vivienda", "Universidad", "Padres", "Servicios", "Servicios Rusia", "Suscripciones",
                    "Gastos financieros", "Comisiones Banco", "Cursos y aprendizaje", "Salud y Bienestar",
                    "Citas médicas", "Medicina", "Cuidado Personal"}

# Medios de pago, en el orden en que mas se usan.
MEDIOS = ["T-Bank", "Falabella", "Interbank", "Binance", "PayPal", "Sberbank", "Payoneer", "SIP", "KuCoin",
          "Efectivo", "Tarjeta OH", "BBVA", "BCP", "Yape", "Plin"]
# Medios que pueden ser tarjeta de credito o de debito: el formulario de gasto pregunta cual.
TARJETAS = ["T-Bank", "Falabella", "Interbank", "Sberbank", "SIP", "Tarjeta OH", "BBVA", "BCP"]
# Nombre de la deuda (base Deudas) donde se acumula lo que se compra a credito con cada tarjeta.
BILLETERA_BANCO = {"Plin": "Interbank", "Yape": "BCP"}   # pagar con Plin/Yape sale de esa cuenta del banco
BILLETERA_OTROS = {"Yape": ["Interbank"]}                 # ... a veces de otra: el bot ofrece un boton para cambiarla
DEUDA_TARJETA = {"Tarjeta OH": "Tarjeta OH", "Falabella": "Banco Falabella"}   # "Banco Falabella" es la tarjeta; el préstamo va en otra deuda aparte
BANCO_TARJETA = {"Falabella": "Banco Falabella", "T-Bank": "T-Bank (Tinkoff)", "Tarjeta OH": "Financiera OH",
                 "SIP": "Banco SIP"}


def deuda_de_tarjeta(medio: str) -> str:
    return DEUDA_TARJETA.get(medio) or "Tarjeta " + medio


# Otras formas de escribirlos (y como se llamaban en la hoja de 2025).
ALIAS_MEDIOS = {"tinkoff": "T-Bank", "tinkoft": "T-Bank", "tinkof": "T-Bank", "tbank": "T-Bank", "t bank": "T-Bank",
                "cmr": "Falabella", "saga": "Falabella", "kucoin": "KuCoin", "ku coin": "KuCoin",
                "oh": "Tarjeta OH", "sber": "Sberbank"}

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
    for alias, m in ALIAS_MEDIOS.items():
        if " %s " % alias in t:
            return m
    for m in MEDIOS:
        if " %s " % normal(m) in t:
            return m
    return None
