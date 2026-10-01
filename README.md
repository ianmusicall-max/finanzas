# Finanzas · Telegram → Notion

Sistema personal de **gastos, ingresos, presupuesto, patrimonio y metas de ahorro**.

```
Tú escribes en Telegram "45 almuerzo"  →  bot  →  Notion (base Movimientos)
                                               ↓
                      todos los días 21:30 · domingos 20:00 · día 1 de cada mes
                                               ↓
                 resumen en Telegram  +  fila en la base Resúmenes de Notion
```

Todo vive en el **mismo Notion de Core Forever**, en una página aparte llamada **Finanzas**, y usa la
misma integración (el mismo `NOTION_TOKEN`). El bot de Telegram es **nuevo**, separado de los otros.
Corre en el mismo servidor que Core Forever. Solo usa `requests`, `python-dotenv` y `openpyxl` (este
último, para importar la hoja de 2025).

## Qué hay en Notion

Debajo de la página **Finanzas**, `setup_notion.py` crea cinco bases:

| Base | Qué guarda |
|---|---|
| 💸 **Movimientos** | cada gasto, ingreso, ahorro o inversión: descripción, tipo, categoría, grupo (necesidad/deseo), monto, moneda, tipo de cambio, **monto en soles**, medio de pago, fecha |
| 🧾 **Presupuesto** | tope mensual por categoría |
| 🏦 **Patrimonio** | cuentas, inversiones, cripto, auto, depa (activos) y tarjetas y préstamos (pasivos), con su valor actual |
| 🎯 **Metas** | objetivo, ahorrado y avance (auto, depa, fondo de emergencia…) |
| 📊 **Resúmenes** | una fila por día, semana y mes: ingresos, gastos, ahorro, balance, tasa de ahorro, % necesidades / deseos, patrimonio neto, principales gastos y alertas |

En Notion puedes armarte vistas encima de estas bases: tablero por categoría, gráfico de gastos por mes
(Notion tiene vistas de gráfico), calendario de movimientos, etc. Si editas un movimiento a mano en
Notion, el siguiente resumen ya lo toma.

## Cómo se usa (Telegram)

### Con formulario, como los Google Forms "Gastos 2025" e "Ingresos 2025"

Toca **➖ Gasto**, **➕ Ingreso** o **🐷 Ahorro** en el menú (o escribe `/gasto`, `/ingreso`, `/ahorro`,
`/inversion`). El bot pregunta una cosa por mensaje, con botones:

| Formulario | Preguntas |
|---|---|
| Gasto | fecha · cuenta (Gastos, Salud, Inversión, Educación, Export Latam, Facebook) · medio de pago · categoría · moneda · descripción · importe |
| Ingreso | fecha · dónde entró · categoría (Facebook, Freshtunes, Routenote, Criptomonedas, Ventas…) · moneda · descripción · importe |
| Ahorro | fecha · meta (de la base Metas) · medio de pago · moneda · importe |
| Inversión | fecha · categoría · medio de pago · moneda · descripción · importe |

Al final muestra el resumen con **Guardar**, **Corregir** (vuelves a cualquier pregunta) y **Cancelar**. Nada se
guarda hasta tocar Guardar. Lo último que elegiste en cada pregunta sale primero la próxima vez (si siempre pagas
con T-Bank, T-Bank queda arriba). Las monedas son PEN, RUB, USD y EUR; todo se suma en soles con el tipo de
cambio de `/tc`. Un gasto con cuenta **Inversión** se cuenta como inversión en los resúmenes, no como gasto.

### O rápido, escribiendo como hablas

| Mensaje | Queda como |
|---|---|
| `45 almuerzo` | gasto · Comida y restaurantes · S/ 45 |
| `1200 rub pyaterochka tbank` | gasto en rublos · Supermercado · T-Bank |
| `12.50 taxi yape ayer` | gasto · Movilidad · Yape · fecha de ayer |
| `netflix 44.90` | gasto · Suscripciones |
| `+1943 usd facebook` | ingreso en dólares · Facebook |
| `ahorro 500 emergencia` | ahorro, y suma S/ 500 a la meta "Fondo de emergencia" |
| `120 zapatillas falabella credito` | gasto a crédito: además suma S/ 120 a la deuda "Banco Falabella" (tarjeta y préstamo juntos) |

En el formulario de gasto, si eliges un banco o tarjeta (Falabella, T-Bank, OH, Interbank, BBVA, BCP,
SIP, Sberbank) el bot pregunta **¿Crédito o débito?**. Si es crédito, el gasto cuenta como gasto
y además se suma a la deuda de esa tarjeta en **Deudas** (si no existe, la crea: "Tarjeta BBVA"). Cuando
pagas la tarjeta usas `/pago`, que baja la deuda sin contar otro gasto. Deshacer el gasto también la descuenta.

Después de guardar (por formulario o rápido) aparecen dos botones: **Cambiar categoría** y **Deshacer**. Si el
gasto hace que una categoría pase del 80% o del 100% de su presupuesto, te avisa en ese mismo momento.

| Comando | Qué hace |
|---|---|
| `/hoy` `/ayer` `/semana` `/mes` | resumen del periodo (con comparación contra el anterior) |
| `/presupuesto` | cuánto llevas de cada categoría, con barra y semáforo |
| `/presupuesto comida 800` | fija el tope mensual de una categoría |
| `/patrimonio` | lo que tienes, lo que debes y tu patrimonio neto |
| `/activo Interbank 5200` · `/activo Binance 800 usd` · `/activo Auto 45000` | crea o actualiza un activo |
| `/deuda Tarjeta Falabella 1200` · `/deuda Préstamo BCP 15000` | crea una deuda o actualiza su saldo (base **Deudas**) |
| `/deudas` | cuánto debes, a quién, tasa, cuota y cuánto llevas pagado |
| `/pago Falabella 300` · `/pago Juan 50 usd` | registra un pago: baja el saldo; en 0 la marca como pagada |
| 💳 Deudas → **💸 Pagar …** (o `/pago` solo) | lo mismo con botones: eliges la deuda, cuánto (la cuota, todo u otro monto) y de qué cuenta salió el dinero, que también baja |
| `/metas` · `/meta Auto 100000` | ver metas / crear o cambiar el objetivo |
| `/consejos` | qué mejorar según tus números del mes |
| `/metodos` | formas de manejar tu dinero (50/30/20, págate primero, sobres, base cero, deudas) |
| `/tc 3.72` · `/tc eur 4.05` · `/tc rub 0.046` | tipo de cambio para lo que anotes en dólares, euros o rublos |
| `/ultimos` · `/deshacer` | últimos 10 movimientos / borra el último |
| `/gasto` `/ingreso` `/ahorro` `/inversion` | abre el formulario; con texto después (`/gasto 45 almuerzo`) anota directo |

## Cálculos

- **Tres monedas**: los totales salen en soles, dólares y rublos (`S/ 1,000.00 · $ 295.86 · ₽ 23,364`), con el
  tipo de cambio del día.
- **Tipo de cambio automático**: el bot baja el del día de internet (open.er-api.com, y de respaldo
  fawazahmed0/currency-api) cada 6 horas; cada movimiento guarda el que se usó, así lo anotado antes no
  cambia. `/tc` lo muestra; `/tc 3.38` o `/tc rub 0.0428` lo fija a mano (por ejemplo, el de tu banco) y
  `/tc auto` vuelve a automático. Sin internet usa `TC_USD`, `TC_EUR` y `TC_RUB` del `.env`. En Notion, Movimientos tiene `Monto S/`, `Monto USD` y `Monto RUB`; Deudas tiene
  `Saldo S/`, `Saldo USD` y `Saldo RUB`.

- **Balance** = ingresos − gastos. El **ahorro y la inversión no cuentan como gasto**: son lo que haces con
  el balance. (En la hoja de 2025 el ahorro se sumaba como gasto y por eso el presupuesto marcaba 1145%.)
- **Tasa de ahorro** = balance ÷ ingresos. Meta sana: 20% o más.
- **50/30/20**: cada categoría de gasto es *necesidad* (vivienda, servicios, supermercado, transporte,
  salud, educación, negocio…) o *deseo* (restaurantes, bares, suscripciones, ropa, viajes…). El resumen
  semanal y el mensual muestran qué parte se fue en cada grupo.
- **Presupuesto**: se mide siempre contra lo que va del mes y se compara con cuánto del mes ya pasó
  (ir al 60% del presupuesto el día 10 es una alerta; el día 25, no).
- **Patrimonio neto** = activos − deudas, en soles. Queda registrado en cada resumen, así ves su evolución.
- **Fondo de emergencia**: efectivo y bancos ÷ gasto de un mes normal (el mes pasado). Lo recomendable son 3 a 6 meses.
- **Gastos hormiga**: los de menos de S/ 20; si son muchos y pesan más del 10%, te avisa.

## Cuentas y "págate primero"

- **Saldos de las cuentas**: en Patrimonio, cada cuenta de dinero (Activo · Efectivo y bancos) se reconoce
  por el nombre del banco y la moneda: medio *Interbank* + USD → "Interbank dólares". Un **ingreso** suma al
  saldo de la cuenta donde entró; un **gasto** con débito o efectivo lo resta; un gasto **a crédito** no toca
  la cuenta (va a la deuda de la tarjeta). Deshacer lo revierte. Si la cuenta no existe, el bot sugiere
  crearla con `/activo T-Bank 25000 rub` y el saldo de hoy.
- **Págate primero**: después de cada ingreso el bot pregunta *¿Separas algo para ahorro?* con botones
  10% · 20% · otro monto · no esta vez, y luego la meta (o ahorro general). El ahorro no sale de la
  cuenta: es una parte del dinero que queda marcada para esa meta.

## Presupuesto mensual, anual y gastos fuera del presupuesto

- Cada categoría puede tener tope **mensual** (`/presupuesto suscripciones 100`) y tope **anual** para lo que se
  paga una vez al año (`/presupuesto suscripciones anual 600`). En Notion: columnas `Mensual S/` y `Anual S/`.
- Un pago anual se marca tocando **Anual** en el formulario (solo pregunta en categorías con tope anual) o con la
  palabra *anual*: `120 icloud anual`. Cuenta contra el tope anual y no infla el mes. En Movimientos queda
  `Frecuencia = Anual`.
- **⚠️ Fuera del presupuesto**: un gasto en una categoría sin tope (o un pago anual sin tope anual). Las del día a
  día sin tope no se marcan si hay `/limite`, porque ya las controla el límite. Se avisa al anotarlo y el resumen
  semanal y mensual lista lo imprevisto con su total.

## Suscripciones

Base **Suscripciones** en Notion (nombre, monto, moneda, cada cuántos meses, próximo pago). Al anotar un gasto de
Suscripciones que no está en la lista, el bot pregunta cada cuánto se paga: Mensual · Anual · 3 meses · 6 meses ·
otro número de meses · pago único. Desde ahí la reconoce sola (`20 usd claude`), calcula el próximo pago y avisa
en el resumen diario 3 días antes de cada renovación. El tope **anual** de Suscripciones se ajusta solo con la
lista; el **mensual** es el máximo que fijas tú (`/presupuesto suscripciones 500`) y se compara con el total por
mes (mensuales + anuales repartidas). `/suscripciones` las lista; `/suscripcion cancelar Netflix` la da de baja.

## Límite del día a día

`/limite 1500 rub` fija cuánto puedes gastar por día en el día a día (comida, salidas, transporte, gustos). La
semana vale 7 días y el mes, los días que tenga. No cuentan los gastos fijos del mes (`CATEGORIAS_FIJAS` en
`categorias.py`: vivienda, universidad, padres, servicios, suscripciones, salud…). Después de cada gasto, en
`/hoy`, `/semana`, `/mes` y en los resúmenes automáticos aparece cuánto llevas hoy, en la semana y en el mes,
con 🟢 / 🟡 (80%) / 🔴 (te pasaste) y cuánto te queda por día. `/limite` muestra el estado; `/limite 0` lo quita.

## Excel con gráficos

`/excel` (o el botón 📊 Excel) manda por Telegram un Excel con los datos del momento y un gráfico en cada hoja:
Resumen (tienes vs debes, patrimonio neto, mes y año), Deudas, Cuentas, Metas, Presupuesto del mes, Por mes
(ingresos vs gastos y balance), Categorías (y necesidad vs deseo) y Movimientos del año. Todo en S/, $ y ₽.
Sirve en vez de los gráficos de Notion, que en el plan gratis permite uno solo.

## Gráficos en Notion

Abre la página **Finanzas** en Notion. Cada base tiene pestañas arriba con los gráficos:

| Base | Gráficos |
|---|---|
| **Movimientos** (desde 2026, lo que anotas por Telegram) | 📊 Gastos por categoría · 📈 Ingresos vs gastos por mes · 🍩 Necesidad vs deseo |
| **Historial 2025** (lo importado de la hoja de Google) | los mismos tres y 💳 Gastos por medio de pago |
| **Resúmenes** | 📈 Balance mensual · 🏦 Patrimonio neto |
| **Deudas** | 📉 Saldo por deuda |

En **Deudas** puedes completar a mano la tasa anual, la cuota y el día de pago; el bot los usa en
`/deudas` y en `/consejos` (te dice qué deuda pagar primero, la de mayor tasa).

## Puesta en marcha

1. **Bot nuevo de Telegram.** En **@BotFather**: `/newbot`, nombre "Mis Finanzas", usuario terminado en
   `bot` (por ejemplo `ian_finanzas_bot`). Te da el **token**.
2. **Página en Notion.** Ya está creada la página **Finanzas** en tu Notion (ID `3eb735083904812eaf30c99688fe32c3`, ya puesto en `.env.example`). Ábrela, menú `···` →
   **Conexiones** → conecta **la misma integración que usa Core Forever**. Sin ese paso la integración no
   ve la página y `setup_notion.py` no puede crear las bases.
3. **En el servidor** (el de Core Forever):
   ```bash
   ssh root@TU-SERVIDOR
   git clone https://github.com/ianmusicall-max/finanzas /opt/finanzas
   bash /opt/finanzas/deploy/instalar.sh        # la primera vez crea el .env y se detiene
   nano /opt/finanzas/.env                      # pega los tokens (ver abajo)
   bash /opt/finanzas/deploy/instalar.sh        # ahora sí: crea las bases, prende el bot y los resúmenes
   ```
   En el `.env`: `TELEGRAM_TOKEN` (el del bot nuevo), `NOTION_TOKEN` (cópialo de `/opt/core-forever/.env`),
   `NOTION_PARENT_PAGE_ID` (ya viene puesto). **Nunca pegues tokens en un chat ni los subas a git.**
4. **Tu ID de Telegram.** Escríbele cualquier cosa al bot: te responde tu ID. Pégalo en
   `TELEGRAM_USUARIOS` del `.env` y `systemctl restart finanzas-bot`.
5. **Tu historia de 2025** (opcional). Descarga la hoja "Copia de Finanzas Personales 2025" como .xlsx
   (Archivo → Descargar → Microsoft Excel), súbela al servidor y:
   ```bash
   cd /opt/finanzas
   sudo -u finanzas .venv/bin/python importar_hoja.py Finanzas.xlsx --probar   # muestra qué subiría
   sudo -u finanzas .venv/bin/python importar_hoja.py Finanzas.xlsx            # sube (unos 3 min)
   sudo -u finanzas .venv/bin/python resumen.py mensual --fecha 2025-03-01 --sin-telegram   # rellena resúmenes pasados
   ```
   Sube las pestañas Gastos, Ingresos y Ahorro (las metas). No duplica si lo corres dos veces. Las demás
   pestañas no se leen.

## Resúmenes automáticos

| Cuándo | Qué |
|---|---|
| Todos los días 21:30 | lo que anotaste hoy, cuánto llevas del mes contra el presupuesto, y alertas rojas si las hay |
| Domingo 20:00 | la semana (lunes a domingo): gastos vs. la semana anterior, en qué se fue, 50/30/20, patrimonio y consejos |
| Día 1, 08:00 | el mes que terminó, completo |

Para verlos o forzarlos a mano:
```bash
systemctl list-timers 'finanzas-*'
systemctl start finanzas-resumen@semanal
journalctl -u finanzas-bot -n 50
```

## Actualizar

**Es automático.** El servidor revisa GitHub cada 5 minutos (`finanzas-autoupdate.timer`); si hay algo
nuevo lo baja, corre los tests y reinicia el bot. Si un test falla, vuelve a la versión anterior y el bot
sigue como estaba. Para ver qué hizo: `journalctl -u finanzas-autoupdate -n 20`.

Para forzarlo a mano:

```bash
ssh root@TU-SERVIDOR 'cd /opt/finanzas && git pull -q origin main && bash deploy/actualizar.sh'
```

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -t .
```

## Archivos

| Archivo | Qué hace |
|---|---|
| `bot.py` | el bot: lee Telegram, anota, responde comandos |
| `lector.py` | entiende "12.50 taxi yape ayer" |
| `categorias.py` | categorías, grupos 50/30/20, palabras clave, medios de pago |
| `finanzas.py` | sumas, presupuesto, patrimonio, metas y consejos |
| `informes.py` | textos de los resúmenes y la fila de Resúmenes |
| `resumen.py` | lo que corren los temporizadores |
| `notion.py` · `telegram.py` | clientes mínimos de las dos APIs |
| `setup_notion.py` | crea las bases (y les agrega columnas nuevas cuando las haya) |
| `importar_hoja.py` | sube la hoja de 2025 |
