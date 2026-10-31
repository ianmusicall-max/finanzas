"""Perfil de José Luis: Perú y Rusia, soles como moneda base.

Las categorías salen de la hoja "Finanzas Personales 2025". Cada categoría de gasto tiene un
grupo para la regla 50/30/20: necesidad o deseo.
"""


# Las categorias del formulario "Gastos 2025", en el orden en que mas se usaron.
# categoria -> (grupo 50/30/20, emoji, palabras clave para el modo rapido)
GASTOS = {
    "Restaurantes y cafés": ("Deseo", "🍽", ["restaurante", "cafeteria", "comida", "almuerzo", "cena", "desayuno", "menu", "pollo", "chifa", "ceviche", "pizza", "hamburguesa", "sushi", "rappi", "pedidosya", "delivery", "cafe", "starbucks", "lomo", "aji de gallina", "shawarma"]),
    "Supermercado": ("Necesidad", "🛒", ["mercado", "supermercado", "super", "plaza vea", "wong", "metro", "tottus", "vivanda", "makro", "bodega", "verduras", "fruta", "pan", "abarrotes", "pyaterochka", "perekrestok", "magnit", "lenta", "vkusvill"]),
    "Golosinas": ("Deseo", "🍫", ["golosina", "chocolate", "snack", "gaseosa", "helado", "dulce", "galleta", "papitas", "chatarra"]),
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
MONEDAS = ["PEN", "RUB", "USD", "EUR"]

# Gastos que se pagan una vez al mes y no cuentan para el limite del dia a dia (/limite).
CATEGORIAS_FIJAS = {"Vivienda", "Universidad", "Padres", "Servicios", "Servicios Rusia", "Suscripciones",
                    "Gastos financieros", "Comisiones Banco", "Cursos y aprendizaje", "Salud y Bienestar",
                    "Citas médicas", "Medicina", "Cuidado Personal"}

# Medios de pago, en el orden en que mas se usan.
MEDIOS = ["T-Bank", "Falabella", "Interbank", "Binance", "PayPal", "Sberbank", "Payoneer", "SIP", "KuCoin",
          "Efectivo", "BBVA", "BCP", "Yape", "Plin"]
# Medios que pueden ser tarjeta de credito o de debito: el formulario de gasto pregunta cual.
TARJETAS = ["T-Bank", "Falabella", "Interbank", "Sberbank", "SIP", "BBVA", "BCP"]
# Nombre de la deuda (base Deudas) donde se acumula lo que se compra a credito con cada tarjeta.
BILLETERA_BANCO = {"Plin": "Interbank", "Yape": "Interbank"}  # pagar con Plin/Yape sale de esa cuenta del banco
BILLETERA_OTROS = {"Yape": ["BCP"]}                          # ... a veces de otra: el bot ofrece un boton para cambiarla
# "Banco Falabella" es la tarjeta; el préstamo va en otra deuda aparte. "Tarjeta OH" se dejó apuntando
# a "Banco SIP" para los movimientos viejos: el banco renombró la tarjeta OH a Sip (ver CLAUDE.md, 21/10/2026).
DEUDA_TARJETA = {"SIP": "Banco SIP", "Tarjeta OH": "Banco SIP", "Falabella": "Banco Falabella"}
BANCO_TARJETA = {"Falabella": "Banco Falabella", "T-Bank": "T-Bank (Tinkoff)", "SIP": "Banco SIP",
                 "Tarjeta OH": "Banco SIP"}



# Otras formas de escribirlos (y como se llamaban en la hoja de 2025).
ALIAS_MEDIOS = {"tinkoff": "T-Bank", "tinkoft": "T-Bank", "tinkof": "T-Bank", "tbank": "T-Bank", "t bank": "T-Bank",
                "cmr": "Falabella", "saga": "Falabella", "kucoin": "KuCoin", "ku coin": "KuCoin",
                "oh": "SIP", "tarjeta oh": "SIP", "financiera oh": "SIP", "sber": "Sberbank"}

# Clases de patrimonio: (clase, tipo)


# Categorias que cambiaron de nombre (09/10/2026 en adelante). Lo que ya estaba guardado en Notion
# conserva el nombre viejo, asi que al leerlo se traduce al nuevo: el historial, el presupuesto y los
# resumenes siguen contando todo junto en vez de partirse en dos lineas.
RENOMBRADAS = {
    "Comida y restaurantes": "Restaurantes y cafés",
    "Chatarra y golosinas": "Golosinas",
}


# La categoria donde cae lo que no encaja en ninguna otra. `categorias.otros()` la usa, y
# `finanzas` la pone cuando una fila de Notion vino sin categoria: tiene que existir arriba.
OTROS = {"Gasto": "Otros", "Ingreso": "Otros ingresos",
         "Ahorro": "Ahorro general", "Inversión": "Otras inversiones"}

# El bot ofrece apartar una parte de cada ingreso, menos cuando el ingreso es justo sacar plata
# del ahorro (`bot.py`). Tiene que ser una de las categorias de INGRESOS de arriba.
RETIRO_AHORRO = "Retiro de ahorro"

# Que botones ve en /start, por filas. Los nombres son los del comando (m:<nombre> en bot.py) y
# el texto de cada uno sale del idioma, no de aca: asi el mismo menu sirve en cualquier idioma.
MENU_OPCIONES = [["gasto", "ingreso", "ahorro"],
                 ["retirar", "reloj"],
                 ["hoy", "semana", "mes"],
                 ["limite", "presupuesto", "deudas"],
                 ["patrimonio", "metas", "suscripciones"],
                 ["pagos", "proyeccion", "plan"],
                 ["ingresos", "excel", "grafico"],
                 ["comparar", "buscar", "consejos"],
                 ["tc", "ajustar"]]
