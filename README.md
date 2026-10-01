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
con Tinkoff, Tinkoff queda arriba). Las monedas son PEN, RUB, USD y EUR; todo se suma en soles con el tipo de
cambio de `/tc`. Un gasto con cuenta **Inversión** se cuenta como inversión en los resúmenes, no como gasto.

### O rápido, escribiendo como hablas

| Mensaje | Queda como |
|---|---|
| `45 almuerzo` | gasto · Comida y restaurantes · S/ 45 |
| `1200 rub pyaterochka tinkoff` | gasto en rublos · Supermercado · Tinkoff |
| `12.50 taxi yape ayer` | gasto · Movilidad · Yape · fecha de ayer |
| `netflix 44.90` | gasto · Suscripciones |
| `+1943 usd facebook` | ingreso en dólares · Facebook |
| `ahorro 500 emergencia` | ahorro, y suma S/ 500 a la meta "Fondo de emergencia" |

Después de guardar (por formulario o rápido) aparecen dos botones: **Cambiar categoría** y **Deshacer**. Si el
gasto hace que una categoría pase del 80% o del 100% de su presupuesto, te avisa en ese mismo momento.

| Comando | Qué hace |
|---|---|
| `/hoy` `/ayer` `/semana` `/mes` | resumen del periodo (con comparación contra el anterior) |
| `/presupuesto` | cuánto llevas de cada categoría, con barra y semáforo |
| `/presupuesto comida 800` | fija el tope mensual de una categoría |
| `/patrimonio` | lo que tienes, lo que debes y tu patrimonio neto |
| `/activo Interbank 5200` · `/activo Binance 800 usd` · `/activo Auto 45000` | crea o actualiza un activo |
| `/deuda Tarjeta Ripley 1200` · `/deuda Préstamo BCP 15000` | crea o actualiza una deuda |
| `/metas` · `/meta Auto 100000` | ver metas / crear o cambiar el objetivo |
| `/consejos` | qué mejorar según tus números del mes |
| `/metodos` | formas de manejar tu dinero (50/30/20, págate primero, sobres, base cero, deudas) |
| `/tc 3.72` · `/tc eur 4.05` · `/tc rub 0.046` | tipo de cambio para lo que anotes en dólares, euros o rublos |
| `/ultimos` · `/deshacer` | últimos 10 movimientos / borra el último |
| `/gasto` `/ingreso` `/ahorro` `/inversion` | abre el formulario; con texto después (`/gasto 45 almuerzo`) anota directo |

## Cálculos

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

## Puesta en marcha

1. **Bot nuevo de Telegram.** En **@BotFather**: `/newbot`, nombre "Mis Finanzas", usuario terminado en
   `bot` (por ejemplo `ian_finanzas_bot`). Te da el **token**.
2. **Página en Notion.** Ya está creada la página **Finanzas** en tu Notion (ID `3eb735083904812eaf30c99688fe32c3`, ya puesto en `.env.example`). Ábrela, menú `···` →
   **Conexiones** → conecta **la misma integración que usa Core Forever**. Sin ese paso la integración no
   ve la página y `setup_notion.py` no puede crear las bases.
3. **En el servidor** (el de Core Forever):
   ```bash
   ssh root@67.205.160.34
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

```bash
ssh root@67.205.160.34 'bash /opt/finanzas/deploy/actualizar.sh'
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
