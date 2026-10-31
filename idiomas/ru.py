"""Русский. Los mismos botones que en español, con el nombre en ruso."""

BOTONES = {
    "gasto": "➖ Расход", "ingreso": "➕ Доход", "ahorro": "🐷 Накопления", "inversion": "📈 Вложения",
    "retirar": "🏧 Снять наличные", "reloj": "⏱ Таймер",
    "hoy": "📅 Сегодня", "semana": "🗓 Неделя", "mes": "📆 Месяц",
    "limite": "📏 Лимит", "presupuesto": "🧾 Бюджет", "deudas": "💳 Долги",
    "patrimonio": "🏦 Капитал", "metas": "🎯 Цели", "suscripciones": "🔁 Подписки",
    "pagos": "🔔 Платежи", "proyeccion": "📈 Прогноз", "plan": "📉 План долгов",
    "ingresos": "💰 Доходы", "excel": "📗 Excel", "grafico": "🖼 График",
    "comparar": "📊 Сравнить", "buscar": "🔍 Поиск", "consejos": "💡 Советы",
    "tc": "💱 Курс", "ajustar": "⚙️ Настройки", "ver": "👁 Посмотреть",
}

DIAS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

# En ruso el mes cambia de forma: "31 октября" (con el dia) pero "октябрь" (solo). MESES es el
# que acompana a un numero, que es como se usa en las fechas; MESES_SOLO el que va suelto.
# En espanol los dos son el mismo, por eso en es.py hay una sola lista.
MESES = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
         "сентября", "октября", "ноября", "декабря"]
MESES_SOLO = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август",
              "сентябрь", "октябрь", "ноябрь", "декабрь"]

# El nombre de la cuenta de efectivo en Notion: "Наличные", "Наличные доллары"...
EFECTIVO = "Наличные"
MONEDA_NOMBRE = {"USD": "доллары", "PEN": "соли", "EUR": "евро", "RUB": "рубли"}

TEXTOS = {
    # ---------------------------------------------------------------- formularios
    "➖ Nuevo gasto": "➖ Новый расход",
    "➕ Nuevo ingreso": "➕ Новый доход",
    "🐷 Nuevo ahorro": "🐷 Новое накопление",
    "📈 Nueva inversión": "📈 Новое вложение",

    "📅 ¿Qué fecha?": "📅 Какая дата?",
    "🏦 ¿De qué cuenta sale?\n<i>El banco, la billetera o el efectivo con el que pagaste.</i>":
        "🏦 С какого счёта?\n<i>Банк, кошелёк или наличные, которыми вы заплатили.</i>",
    "🏦 ¿A qué cuenta entró el dinero?": "🏦 На какой счёт пришли деньги?",
    "🗓 ¿Es un pago del mes o un pago anual?\n<i>Los anuales (por ejemplo iCloud o la VPN del año) "
    "cuentan contra el presupuesto anual, no contra el del mes.</i>":
        "🗓 Это платёж за месяц или за год?\n<i>Годовые (например iCloud или VPN на год) идут "
        "в годовой бюджет, а не в месячный.</i>",
    "💳 ¿Crédito o débito?\n<i>Si es crédito, se suma a la deuda de esa tarjeta.</i>":
        "💳 Кредит или дебет?\n<i>Если кредит, сумма добавится к долгу по этой карте.</i>",
    "🧾 ¿En cuántas cuotas?\n<i>Si lo pagas todo en el próximo estado de cuenta, "
    "elige «Un solo pago».</i>":
        "🧾 На сколько частей?\n<i>Если платите всё в следующей выписке, выберите «Один платёж».</i>",
    "🏷 ¿Qué categoría?": "🏷 Какая категория?",
    "🎯 ¿Para qué meta es?": "🎯 На какую цель?",
    "💱 ¿En qué moneda?": "💱 В какой валюте?",
    "📝 Escribe una descripción corta (por ejemplo: <i>almuerzo con Ana</i>).":
        "📝 Напишите короткое описание (например: <i>обед с Аней</i>).",
    "💰 ¿Cuánto fue? Escribe solo el número (por ejemplo: <code>45.50</code>).":
        "💰 Сколько получилось? Напишите только число (например: <code>450</code>).",

    # etiquetas del resumen y del menu de corregir
    "Fecha": "Дата",
    "Medio de pago": "Счёт",
    "Tarjeta": "Карта",
    "Cuotas": "Части",
    "Pago": "Платёж",
    "Categoría": "Категория",
    "Meta": "Цель",
    "Moneda": "Валюта",
    "Descripción": "Описание",
    "Importe": "Сумма",

    # opciones que llegan por variable: el VALOR sigue en espanol (va a Notion y se compara),
    # esto es solo lo que se lee en el boton.
    "Débito": "Дебет",
    "Crédito": "Кредит",
    "Un solo pago": "Один платёж",
    "%s cuotas": "%s частей",
    "Mensual": "Ежемесячный",
    "Anual": "Годовой",
    "Sin meta (ahorro general)": "Без цели (общие накопления)",

    # botones y fechas
    "✖️ Cancelar": "✖️ Отмена",
    "✅ Guardar": "✅ Сохранить",
    "✏️ Corregir": "✏️ Исправить",
    "Omitir": "Пропустить",
    "Hoy %s": "Сегодня %s",
    "Ayer": "Вчера",
    "Anteayer": "Позавчера",
    "hoy (%s)": "сегодня (%s)",
    "ayer (%s)": "вчера (%s)",
    "\n<i>O escribe la fecha: 15/09</i>": "\n<i>Или напишите дату: 15/09</i>",

    # respuestas del formulario
    "Cancelado. No se guardó nada.": "Отменено. Ничего не сохранено.",
    "<b>%s</b> · revisa antes de guardar": "<b>%s</b> · проверьте перед сохранением",
    "¿Qué quieres corregir?": "Что исправить?",
    "Ese botón era de una pregunta anterior.": "Эта кнопка — от предыдущего вопроса.",
    "Toca Guardar, Corregir o Cancelar.": "Нажмите «Сохранить», «Исправить» или «Отмена».",
    "No entendí la fecha. Escríbela así: <code>15/09</code> o toca un botón.":
        "Не понял дату. Напишите так: <code>15/09</code> — или нажмите кнопку.",
    "Esa fecha no existe. Prueba otra vez.": "Такой даты не существует. Попробуйте ещё раз.",
    "Escribe solo el número, por ejemplo <code>45.50</code>.":
        "Напишите только число, например <code>450</code>.",
    "El importe tiene que ser mayor que cero.": "Сумма должна быть больше нуля.",
    "Elige una de las opciones con los botones.": "Выберите один из вариантов кнопками.",
    "Ese formulario ya no está (me reinicié). Empezamos de nuevo:":
        "Эта форма уже закрыта (бот перезапустился). Начнём заново:",

    # lo que se guarda en Notion
    "Ahorro": "Накопление",
    "Ahorro para %s": "Накопление на %s",
    # ---------------------------------------------------------------- pantalla de inicio
    "💰 <b>Finanzas</b> · %s %d de %s": "💰 <b>Финансы</b> · %s, %d %s",
    "💰 <b>Finanzas</b> · %s %d de %s\n": "💰 <b>Финансы</b> · %s, %d %s\n",
    "📏 %s hoy: %s": "📏 %s сегодня: %s",
    "Te pasaste": "Перерасход",
    "Quedan": "Осталось",
    "📏 <b>Para gastar en el día a día</b>": "📏 <b>На повседневные траты</b>",
    "📏 Fija cuánto puedes gastar por día y aquí verás cuánto te queda hoy, en la semana y en el mes: "
    "<code>/limite %s</code>":
        "📏 Задайте, сколько можно тратить в день, и здесь будет видно, сколько осталось "
        "на сегодня, на неделю и на месяц: <code>/limite %s</code>",
    "Escribe cuánto puedes gastar por día: <code>/limite %s</code>":
        "Напишите, сколько можно тратить в день: <code>/limite %s</code>",
    "💳 Deudas: <b>%s</b>%s": "💳 Долги: <b>%s</b>%s",
    " · cuotas %s al mes": " · платёж %s в месяц",
    "🔔 Hoy toca: %s%s": "🔔 Сегодня: %s%s",
    "%s Si no entra más dinero, cierras el mes con %s":
        "%s Если больше денег не поступит, месяц закроется с %s",
    "🔁 %s se renueva el %s": "🔁 %s продлевается %s",
    "<i>⚠️ Notion no respondió; prueba /start en un rato.</i>":
        "<i>⚠️ Notion не ответил; попробуйте /start чуть позже.</i>",
    "Anotar: /gasto · /ingreso · /ahorro · /inversion\nTodos los comandos: /ayuda":
        "Записать: /gasto · /ingreso · /ahorro\nВсе команды: /ayuda",
    "🐷 Ahorro general": "🐷 Общие накопления",

    # ---------------------------------------------------------------- /ayuda
    # Solo los comandos que ella usa. Los demas siguen existiendo, pero llenarle la ayuda de
    # deudas y tarjetas de credito que no tiene es ruido.
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
    "/comparar · este mes contra el pasado, categoría por categoría\n"
    "/proyeccion · cómo cierras el mes si no entra más dinero\n"
    "/plan · cuándo terminas de pagar tus deudas (y con extra: /plan 300 usd)\n"
    "/ingresos · cuánto deja cada fuente, mes a mes\n"
    "/grafico · imagen con los gastos de la semana\n"
    "/consejos · qué mejorar según tus números\n"
    "/metodos · formas de manejar tu dinero\n"
    "/ultimos · lo último que anotaste, con botones para corregir el monto o borrar\n"
    "/reloj · botones de 30 min, 1 hora o 3 horas; eliges uno, escribes qué haces y te aviso\n"
    "/reloj fin · cierra el bloque y te dice cuánto tomó y tu promedio · /reloj tareas\n"
    "<code>/buscar farmacia</code> · busca en todo tu historial (<code>/buscar uber mes</code>)\n\n"
    "<b>Ajustar</b>\n"
    "<code>/presupuesto comida 800</code>\n"
    "<code>/activo Interbank 5200</code> · <code>/deuda Tarjeta Falabella 1200</code>\n"
    "<code>/pago Falabella 300</code> · baja el saldo de una deuda\n"
    "<code>/corte Falabella 10</code> · el día que cierra el estado de cuenta de una tarjeta\n"
    "<code>/meta Auto 100000</code>\n"
    "<code>/tc 3.72</code> · <code>/tc rub 0.046</code> · tipo de cambio\n"
    "/deshacer · borra lo último que anotaste (para uno viejo, /ultimos)":
        "💰 <b>Финансы</b> · всё сохраняется в Notion\n\n"
        "<b>Записать</b> (кнопками):\n"
        "<code>450 обед</code> · можно просто написать сумму и что это было\n"
        "/gasto · /ingreso · /ahorro\n\n"
        "<b>Посмотреть</b>\n"
        "/hoy · /ayer · /semana · /mes · сводки\n"
        "/limite · сколько потрачено сегодня, за неделю и за месяц\n"
        "/presupuesto · сколько ушло по каждой категории\n"
        "/comparar · этот месяц против прошлого, по категориям\n"
        "/metas · продвижение по целям накоплений\n"
        "/proyeccion · с чем закроется месяц, если больше денег не поступит\n"
        "/ingresos · сколько приносит каждый источник, месяц за месяцем\n"
        "/consejos · что улучшить, судя по вашим цифрам\n"
        "/excel · всё в Excel с графиками\n"
        "/ultimos · последние записи, с кнопками исправить сумму или удалить\n"
        "/reloj · таймер на задачу: выбираете срок, пишете чем заняты, и бот напомнит\n"
        "/reloj fin · закрыть блок: сколько заняло и каково среднее · /reloj tareas\n"
        "<code>/buscar аптека</code> · поиск по всей истории (<code>/buscar такси месяц</code>)\n\n"
        "<b>Настроить</b>\n"
        "<code>/limite 1500</code> · сколько можно тратить в день\n"
        "<code>/presupuesto кафе 8000</code>\n"
        "<code>/meta Отпуск 100000</code>\n"
        "<code>/activo Сбер 50000</code> · сколько лежит на счету\n"
        "<code>/tc 83</code> · <code>/tc pen 22</code> · курс валют\n"
        "/deshacer · удалить последнюю запись (для старой — /ultimos)",
}

# ---------------------------------------------------------------- Notion
# Como se llaman en SU Notion las bases y las columnas. El codigo las sigue nombrando en
# espanol: la traduccion pasa solo en la frontera (notion.fila / crear_pagina / consultar),
# asi no hubo que tocar los cientos de sitios que dicen f.get("Monto").
#
# El simbolo o el codigo de moneda del final no va aca: "Monto ₽" se arma solo (notion.n_prop).
NOTION_PROP = {
    # las bases
    "Movimientos": "Движения", "Presupuesto": "Бюджет", "Patrimonio": "Капитал",
    "Metas": "Цели", "Resúmenes": "Сводки", "Deudas": "Долги",
    "Suscripciones": "Подписки", "Recordatorios": "Напоминания",

    # columnas comunes
    "Descripción": "Описание", "Tipo": "Тип", "Categoría": "Категория", "Grupo": "Группа",
    "Cuenta": "Счёт", "Monto": "Сумма", "Moneda": "Валюта", "Tipo de cambio": "Курс",
    "Medio de pago": "Способ оплаты", "Tarjeta": "Карта", "Cuotas": "Части",
    "Frecuencia": "Периодичность", "Fecha": "Дата", "Origen": "Источник", "Creado": "Создано",
    "Notas": "Заметки", "Nombre": "Название", "Estado": "Статус", "Día": "День",

    # presupuesto
    "Mensual": "Бюджет месяца", "Anual": "Бюджет года",

    # patrimonio
    "Clase": "Класс", "Valor": "Стоимость", "Actualizado": "Обновлено",

    # metas
    "Meta": "Цель", "Objetivo": "Сколько нужно", "Ahorrado": "Накоплено",
    "Avance": "Прогресс", "Prioridad": "Приоритет", "Fecha límite": "Срок",

    # resumenes
    "Periodo": "Период", "Fechas": "Даты", "Ingresos": "Доходы", "Gastos": "Расходы",
    "Ahorro": "Накопления", "Inversión": "Вложения", "Balance": "Баланс",
    "Tasa de ahorro": "Норма сбережений", "Necesidades %": "Нужное %", "Deseos %": "Желания %",
    "Patrimonio neto": "Чистый капитал", "Principales gastos": "Главные расходы",
    "Alertas": "Предупреждения",

    # recordatorios y suscripciones
    "Recordatorio": "Напоминание", "Deuda": "Долг", "Último": "Последний",
    "Próxima fecha": "Следующая дата", "Suscripción": "Подписка",
    "Cada (meses)": "Каждые (месяцев)", "Por mes": "В месяц",
    "Último pago": "Последний платёж", "Próximo pago": "Следующий платёж",

    # deudas
    "Acreedor": "Кредитор", "Monto original": "Изначальная сумма", "Saldo": "Остаток",
    "Tasa anual": "Годовая ставка", "Cuota mensual": "Платёж в месяц",
    "Día de corte": "День выписки", "Día de pago": "День платежа", "Inicio": "Начало",
}

# Los valores de las columnas que son llaves del sistema (notion.COLUMNAS_LLAVE). Las
# categorias, los medios de pago y las monedas NO estan aca: salen del perfil y ya vienen
# en ruso.
NOTION_VALOR = {
    # Tipo de movimiento
    "Gasto": "Расход", "Ingreso": "Доход", "Ahorro": "Накопление", "Inversión": "Вложение",
    # Grupo
    "Necesidad": "Нужное", "Deseo": "Желание",
    # Cuenta
    "Gastos": "Расходы", "Salud": "Здоровье", "Educación": "Обучение",
    # Tarjeta y frecuencia
    "Débito": "Дебет", "Crédito": "Кредит", "Mensual": "Ежемесячный", "Anual": "Годовой",
    # Origen
    "Telegram": "Telegram", "Hoja 2025": "Таблица 2025", "Manual": "Вручную",
    # Patrimonio
    "Activo": "Актив", "Pasivo": "Пассив", "Efectivo y bancos": "Наличные и счета",
    "Inversiones": "Вложения", "Cripto": "Крипто", "Inmueble": "Недвижимость",
    "Vehículo": "Транспорт", "Por cobrar": "К получению", "Otro activo": "Другой актив",
    "Tarjeta de crédito": "Кредитная карта", "Préstamo": "Заём", "Hipoteca": "Ипотека",
    "Por pagar": "К оплате", "Otra deuda": "Другой долг",
    # Metas
    "Muy importante": "Очень важно", "Importante": "Важно", "Puede esperar": "Может подождать",
    # Resumenes
    "Diario": "Ежедневная", "Semanal": "Еженедельная",
    # Recordatorios
    "Pago": "Платёж", "Deuda": "Долг", "Retiro": "Снятие", "Otro": "Другое",
    # Suscripciones y deudas
    "Pausado": "На паузе", "Activa": "Активна", "Cancelada": "Отменена",
    "Persona": "Человек", "Otra": "Прочее", "Pagada": "Погашен",
}
