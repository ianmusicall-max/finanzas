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
    "ultimos": "🧾 Последние", "pago": "💸 Погасить долг", "deshacer": "↩️ Отменить последнее",
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
        "на сегодня, на неделю и на месяц: <code>/limit %s</code>",
    "Escribe cuánto puedes gastar por día: <code>/limite %s</code>":
        "Напишите, сколько можно тратить в день: <code>/limit %s</code>",
    "💳 Deudas: <b>%s</b>%s": "💳 Долги: <b>%s</b>%s",
    " · cuotas %s al mes": " · платёж %s в месяц",
    "🔔 Hoy toca: %s%s": "🔔 Сегодня: %s%s",
    "%s Si no entra más dinero, cierras el mes con %s":
        "%s Если больше денег не поступит, месяц закроется с %s",
    "🔁 %s se renueva el %s": "🔁 %s продлевается %s",
    "<i>⚠️ Notion no respondió; prueba /start en un rato.</i>":
        "<i>⚠️ Notion не ответил; попробуйте /start чуть позже.</i>",
    "Anotar: /gasto · /ingreso · /ahorro · /inversion\nTodos los comandos: /ayuda":
        "Записать: /expense · /income · /savings\nВсе команды: /help",
    "🐷 Ahorro general": "🐷 Общие накопления",

    # ---------------------------------------------------------------- ajustes
    "📏 Límite diario": "📏 Лимит на день",
    "📏 ¿Cuánto puedes gastar por día en el día a día?\nEscribe el monto y la moneda, por ejemplo: "
    "<code>1500 rub</code> · <code>64</code> (soles) · <code>19 usd</code>":
        "📏 Сколько можно тратить в день на повседневное?\nНапишите сумму и валюту, например: "
        "<code>1500</code> (рубли) · <code>19 usd</code> · <code>64 pen</code>",
    "🧾 Presupuesto": "🧾 Бюджет",
    "🧾 Escribe la categoría y el tope.\nAl mes: <code>supermercado 855</code> · Pagos de una vez al año: "
    "<code>suscripciones anual 600</code>":
        "🧾 Напишите категорию и предел.\nВ месяц: <code>продукты 20000</code> · Раз в год: "
        "<code>подписки год 6000</code>",
    "🏦 Saldo de una cuenta": "🏦 Остаток на счёте",
    "🏦 Escribe la cuenta y cuánto tiene hoy, por ejemplo: <code>T-Bank 25000 rub</code> · "
    "<code>Interbank dólares 1497 usd</code>":
        "🏦 Напишите счёт и сколько на нём сегодня, например: <code>Т-Банк 25000</code> · "
        "<code>BBVA 1497 usd</code>",
    "💳 Deuda nueva o saldo": "💳 Новый долг или остаток",
    "💳 Escribe la deuda y cuánto debes hoy, por ejemplo: <code>Tarjeta BBVA 1200</code> · "
    "<code>Juan 200 usd</code>":
        "💳 Напишите долг и сколько должны сегодня, например: <code>Карта BBVA 1200</code> · "
        "<code>Аня 200 usd</code>",
    "🎯 Meta de ahorro": "🎯 Цель накоплений",
    "🎯 Escribe la meta y el objetivo, por ejemplo: <code>Viaje a Cusco 5000</code>":
        "🎯 Напишите цель и сколько нужно, например: <code>Отпуск 100000</code>",
    "💱 Tipo de cambio": "💱 Курс валют",
    "💱 Escribe el tipo de cambio: <code>3.38</code> (dólar) · <code>rub 0.0428</code> · "
    "o <code>auto</code> para el del día":
        "💱 Напишите курс: <code>83</code> (доллар) · <code>pen 22</code> · "
        "или <code>auto</code> — курс дня",

    # ---------------------------------------------------------------- reloj
    "⏱ <b>Reloj de trabajo</b>\n¿Cuánto tiempo le das?":
        "⏱ <b>Таймер работы</b>\nСколько времени на это даёте?",
    "⏱ 15 min": "⏱ 15 мин", "⏱ 30 min": "⏱ 30 мин", "⏱ 45 min": "⏱ 45 мин",
    "⏱ 1 hora": "⏱ 1 час", "⏱ 2 horas": "⏱ 2 часа", "⏱ 3 horas": "⏱ 3 часа",
    "⏱ 4 horas": "⏱ 4 часа", "⏱ 6 horas": "⏱ 6 часов", "⏱ 8 horas": "⏱ 8 часов",
    "✏️ Otro": "✏️ Другое", "♾ Sin tope": "♾ Без предела",
    "📊 Mis tiempos": "📊 Моё время",
    "⏹ Terminar": "⏹ Завершить", "✖️ Cortar": "✖️ Сбросить",

    # ---------------------------------------------------------------- al guardar
    # Son los mismos valores que van a Notion, pero el texto de la pantalla puede diferir del
    # nombre de la columna, asi que cada uno tiene su diccionario.
    "Gasto": "Расход", "Ingreso": "Доход", "Ahorro": "Накопление", "Inversión": "Вложение",
    "cuenta %s": "счёт %s", "Gastos": "Расходы", "Salud": "Здоровье", "Educación": "Обучение",

    # ---------------------------------------------------------------- el reloj por dentro
    "%d min": "%d мин",
    "%d h %02d min": "%d ч %02d мин",
    "⏱ Ya tienes <b>%s</b> corriendo, van %s.\nCiérralo con /reloj fin o déjalo con "
    "/reloj corta.":
        "⏱ У вас уже идёт <b>%s</b>, прошло %s.\nЗакройте через /timer stop или сбросьте "
        "через /timer cancel.",
    "¿Qué estás haciendo? Por ejemplo: <code>/reloj facebook 45</code>":
        "Чем вы заняты? Например: <code>/timer фейсбук 45</code>",
    "\nTe aviso a los %d min.": "\nНапомню через %d мин.",
    "\nLa última vez te tomó %s.": "\nВ прошлый раз заняло %s.",
    "\nPromedio de <b>%s</b>: %s (%d veces).": "\nВ среднем <b>%s</b>: %s (раз: %d).",
    "▶️ <b>%s</b>, arrancando.%s": "▶️ <b>%s</b>, начали.%s",
    "No tienes nada corriendo. Arranca con <code>/reloj facebook 45</code>.":
        "Сейчас ничего не идёт. Начните так: <code>/timer фейсбук 45</code>.",
    "⏱ <b>%s</b>: van %s.": "⏱ <b>%s</b>: прошло %s.",
    "\nTe pasaste por %s del tope de %d min.": "\nПревышение на %s от предела в %d мин.",
    "\nQuedan %s de los %d min.": "\nОсталось %s из %d мин.",
    "No tenías nada corriendo.": "Ничего не шло.",
    "⏹ <b>%s</b>: %s.": "⏹ <b>%s</b>: %s.",
    " Te pasaste %s del tope.": " Превышение на %s.",
    " Dentro del tope de %d min. 👏": " Уложились в %d мин. 👏",
    "\n\nPromedio: <b>%s</b> · mejor %s · peor %s (%d veces).":
        "\n\nВ среднем: <b>%s</b> · лучший %s · худший %s (раз: %d).",
    "✖️ <b>%s</b> cortado, no se guardó (iban %s).":
        "✖️ <b>%s</b> сброшен, не сохранено (прошло %s).",
    "👌 Listo, no arranco nada.": "👌 Хорошо, ничего не запускаю.",
    "Ese botón ya no sirve. Empieza otra vez con /reloj.":
        "Эта кнопка уже не работает. Начните заново: /timer.",
    "Escribe solo cuánto tiempo, por ejemplo <code>90</code> minutos, <code>2 horas</code> "
    "o <code>1h30</code>.":
        "Напишите только время, например <code>90</code> минут, <code>2 часа</code> "
        "или <code>1h30</code>.",
    "⏱ %s. ✏️ ¿Y qué vas a hacer?": "⏱ %s. ✏️ А чем будете заняты?",
    "Todavía no has cronometrado nada. Arranca con <code>/reloj facebook 45</code>.":
        "Вы ещё ничего не засекали. Начните так: <code>/timer фейсбук 45</code>.",
    # El ruso tiene tres formas de "veces" (1 раз, 2 раза, 5 раз) y el codigo solo elige entre
    # dos, asi que la frase se escribe con "раз: 5", que vale para cualquier numero, y la
    # palabra suelta queda vacia.
    "• <b>%s</b> · %s de promedio · %d %s": "• <b>%s</b> · в среднем %s · раз: %d%s",
    "vez": "", "veces": "",
    "⏱ <b>Tu tiempo</b>\n\n%s": "⏱ <b>Ваше время</b>\n\n%s",
    "⏰ <b>%s</b>: llegaste al tope de %d min.\n/reloj fin para cerrarlo.":
        "⏰ <b>%s</b>: достигнут предел в %d мин.\n/timer stop — закрыть.",
    "⏰ <b>%s</b>: vas %s, %s pasado del tope.\nNo te vuelvo a molestar.":
        "⏰ <b>%s</b>: прошло %s, превышение на %s.\nБольше не беспокою.",

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
        "/expense · /income · /savings\n\n"
        "<b>Посмотреть</b>\n"
        "/today · /yesterday · /week · /month · сводки\n"
        "/limit · сколько потрачено сегодня, за неделю и за месяц\n"
        "/budget · сколько ушло по каждой категории\n"
        "/compare · этот месяц против прошлого, по категориям\n"
        "/goals · продвижение по целям накоплений\n"
        "/forecast · с чем закроется месяц, если больше денег не поступит\n"
        "/earnings · сколько приносит каждый источник, месяц за месяцем\n"
        "/tips · что улучшить, судя по вашим цифрам\n"
        "/excel · всё в Excel с графиками\n"
        "/last · последние записи, с кнопками исправить сумму или удалить\n"
        "/timer · таймер на задачу: выбираете срок, пишете чем заняты, и бот напомнит\n"
        "/timer stop · закрыть блок: сколько заняло и каково среднее · /timer tasks\n"
        "<code>/search аптека</code> · поиск по всей истории (<code>/search такси месяц</code>)\n\n"
        "<b>Настроить</b>\n"
        "<code>/limit 1500</code> · сколько можно тратить в день\n"
        "<code>/budget кафе 8000</code>\n"
        "<code>/goal Отпуск 100000</code>\n"
        "<code>/asset Сбер 50000</code> · сколько лежит на счету\n"
        "<code>/rate 83</code> · <code>/rate pen 22</code> · курс валют\n"
        "/undo · удалить последнюю запись (для старой — /last)\n\n"
        "<i>Команды латиницей: Telegram не принимает кириллицу в командах. "
        "Старые испанские названия тоже работают.</i>",
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

# ---------------------------------------------------------------- los comandos
# Telegram NO acepta comandos en cirilico: solo letras latinas, numeros y guion bajo. Un
# "/расход" no seria un enlace azul ni saldria en el menu de "/". Asi que van en ingles, que
# es lo que mas se entiende sin ser espanol.
#
# La clave es como lo nombra el codigo; el valor, como lo escribe ella. Los nombres en espanol
# SIGUEN funcionando (el bot despacha sobre ellos), asi que un mensaje viejo o un enlace de
# antes no se rompe.
COMANDOS = {
    "gasto": "expense", "ingreso": "income", "ahorro": "savings", "inversion": "investment",
    "retirar": "cash", "reloj": "timer", "pomodoro": "pomodoro",
    "hoy": "today", "ayer": "yesterday", "semana": "week", "mes": "month",
    "limite": "limit", "presupuesto": "budget", "comparar": "compare",
    "deudas": "debts", "deuda": "debt", "pago": "pay", "plan": "plan", "corte": "cutoff",
    "patrimonio": "networth", "activo": "asset",
    "metas": "goals", "meta": "goal",
    "suscripciones": "subscriptions", "pagos": "payments",
    "proyeccion": "forecast", "ingresos": "earnings", "consejos": "tips",
    "metodos": "methods", "grafico": "chart", "excel": "excel",
    "buscar": "search", "ultimos": "last", "deshacer": "undo", "cancelar": "cancel",
    "tc": "rate", "ayuda": "help",
}
