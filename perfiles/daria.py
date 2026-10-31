"""Perfil de Дарья: Moscú, rublos como moneda base, sin deudas y sin tarjetas de crédito.

Las categorías y los emojis son los que ella eligió (30/10/2026). Las palabras clave están en
ruso para que el modo rápido funcione: escribe «450 продукты» y el bot sabe dónde va.

**Todas sus tarjetas son de débito.** La maquinaria de crédito (corte, día de pago, cuotas) queda
dormida: `TARJETAS` vacío. Cuando tenga una tarjeta de crédito se agrega ahí y a `DEUDA_TARJETA`,
y todo lo demás ya está construido.
"""

# categoria -> (grupo 50/30/20, emoji, palabras clave para el modo rapido)
GASTOS = {
    "Квартира": ("Necesidad", "🏠", ["квартира", "аренда", "жилье", "жкх", "квартплата", "коммуналка"]),
    "Продукты": ("Necesidad", "🥑", ["продукты", "еда", "магазин", "супермаркет", "пятерочка", "перекресток",
                                     "вкусвилл", "лента", "магнит", "ашан", "овощи", "фрукты", "хлеб", "молоко"]),
    "Кафе": ("Deseo", "🍰", ["кафе", "ресторан", "кофе", "кофейня", "обед", "завтрак", "ужин", "столовая",
                             "доставка", "бар", "пицца", "суши", "шаурма"]),
    "Транспорт": ("Necesidad", "🚊", ["транспорт", "метро", "автобус", "трамвай", "троллейбус", "такси",
                                      "тройка", "электричка", "самокат", "яндекс го", "каршеринг"]),
    "Красота": ("Deseo", "🌞", ["красота", "салон", "парикмахер", "стрижка", "маникюр", "педикюр", "ногти",
                                "брови", "ресницы", "косметика", "крем", "шампунь"]),
    "Спорт": ("Deseo", "🏃‍♀️", ["спорт", "зал", "фитнес", "йога", "бассейн", "тренировка", "абонемент"]),
    "Здоровье": ("Necesidad", "💊", ["здоровье", "аптека", "врач", "лекарства", "лекарство", "таблетки",
                                     "анализы", "стоматолог", "клиника", "больница", "приём"]),
    "Одежда": ("Deseo", "🛍️", ["одежда", "обувь", "куртка", "платье", "джинсы", "футболка", "белье",
                                "носки", "сумка", "кроссовки"]),
    "Путешествие": ("Deseo", "🗺️", ["путешествие", "поездка", "билеты", "билет", "самолет", "поезд",
                                     "отель", "гостиница", "виза", "аэропорт"]),
    "Развлечения": ("Deseo", "🪄", ["развлечения", "кино", "театр", "концерт", "музей", "выставка",
                                    "книги", "книга", "игры", "подарок другу"]),
    "Обучение": ("Necesidad", "📚", ["обучение", "курс", "курсы", "учеба", "репетитор", "вебинар",
                                     "школа", "университет"]),
    # Wi-Fi, internet, telefono y suscripciones, todo junto: es como ella lo pidio.
    "Подписки": ("Necesidad", "📲", ["подписки", "подписка", "интернет", "вайфай", "вай фай", "wifi",
                                     "связь", "мобильная связь", "телефон", "мтс", "билайн", "мегафон",
                                     "теле2", "йота", "яндекс плюс", "netflix", "spotify"]),
    "Разное": ("Deseo", "🔖", ["разное", "прочее"]),
}

INGRESOS = {
    "Зарплата": ("💼", ["зарплата", "зп", "оклад", "работа"]),
    "Подработка": ("✨", ["подработка", "фриланс", "заказ", "халтура"]),
    "Подарки": ("🎁", ["подарок", "подарки", "подарили"]),
    "Снятие с накоплений": ("🐷", ["снятие", "с накоплений", "со вклада"]),
    "Прочие доходы": ("➕", ["прочий доход", "прочее"]),
}

AHORROS = {
    "Резерв": ("🛡", ["резерв", "подушка", "на всякий случай"]),
    "Цели": ("🎯", ["цель", "цели"]),
    "Накопления": ("🐷", ["накопления", "копить"]),
}

INVERSIONES = {
    "Вклад": ("🏦", ["вклад", "депозит", "проценты"]),
    "Прочие вложения": ("📈", ["вложение", "вложения", "инвестиции"]),
}

# Rublos primero: es la moneda base. El dolar y el sol se convierten al cambio del dia.
MONEDAS = ["RUB", "USD", "PEN"]

# Las otras dos monedas que salen al lado de cada monto (F.s3). La base no va aca.
# El dolar y el sol: lo que le llega de Peru.
# Cuanto propone el bot como limite del dia a dia, en la MONEDA_BASE (solo un ejemplo).
LIMITE_EJEMPLO = 1500
MONEDAS_RESUMEN = ["USD", "PEN"]

# Lo que se paga una vez al mes y no cuenta para el limite del dia a dia.
CATEGORIAS_FIJAS = {"Квартира", "Подписки"}

# Medios de pago, en el orden en que mas se usan. Сбер es la cuenta principal.
MEDIOS = ["Сбер", "Т-Банк", "РСХБ", "СБП", "Наличные", "UnionPay", "BBVA", "BBVA Compras"]
# Ninguna es de credito todavia, asi que el formulario no pregunta "credito o debito".
TARJETAS = []

# Pagar por СБП sale de la cuenta principal.
BILLETERA_BANCO = {"СБП": "Сбер"}
BILLETERA_OTROS = {}

DEUDA_TARJETA = {}
BANCO_TARJETA = {}

ALIAS_MEDIOS = {"сбер": "Сбер", "сбербанк": "Сбер", "sber": "Сбер",
                "тбанк": "Т-Банк", "т банк": "Т-Банк", "тинькофф": "Т-Банк", "tinkoff": "Т-Банк",
                "рсхб": "РСХБ", "россельхоз": "РСХБ", "россельхозбанк": "РСХБ",
                "сбп": "СБП", "наличка": "Наличные", "нал": "Наличные", "кэш": "Наличные",
                "юнионпей": "UnionPay", "unionpay": "UnionPay",
                "compras": "BBVA Compras", "ббва": "BBVA"}

# Nada renombrado todavia.
RENOMBRADAS = {}

OTROS = {"Gasto": "Разное", "Ingreso": "Прочие доходы",
         "Ahorro": "Накопления", "Inversión": "Прочие вложения"}

# Cuando se aparta plata: a que categoria va segun si es para la reserva, para una meta
# con nombre, o sin destino (esa ultima es OTROS["Ahorro"]). Las dos tienen que estar en
# AHORROS de arriba. Antes estaban escritas a mano en espanol dentro del codigo.
AHORRO_EMERGENCIA = "Резерв"
AHORRO_METAS = "Цели"

RETIRO_AHORRO = "Снятие с накоплений"

# Menu corto a proposito: no tiene deudas, ni tarjetas de credito, ni patrimonio que sumar, asi
# que esos botones solo le ocuparian la pantalla. Los comandos siguen existiendo (/deudas,
# /patrimonio...) por si algun dia le hacen falta; simplemente no estan a la vista.
MENU_OPCIONES = [["gasto", "ingreso", "ahorro"],
                 ["hoy", "semana", "mes"],
                 ["limite", "presupuesto", "comparar"],
                 ["reloj", "buscar", "excel"],
                 ["tc", "ajustar"]]
