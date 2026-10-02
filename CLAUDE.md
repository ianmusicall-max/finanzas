# Finanzas · contexto para Claude Code

Bot de Telegram de finanzas personales que guarda todo en Notion. El dueño no es programador:
explicarle en español, simple, con pasos de una sola línea para la Terminal de su Mac.

## Reglas

- **Repositorio público**: nunca subir tokens, contraseñas, la IP del servidor, montos reales ni archivos
  con datos personales (Excel, exportaciones). Los tokens viven solo en `/opt/finanzas/.env` del servidor.
- Antes de cada commit: `.venv/bin/python -m unittest discover -s tests -t .` tiene que dar OK.
  Los tests no salen a internet (`tests/__init__.py` pone `TC_AUTO=0`).
- Solo dependencias `requests`, `python-dotenv` y `openpyxl`.
- Cada cambio visible para el usuario va también en `README.md` y, si es un comando, en `AYUDA` de `bot.py`.

## Cómo está armado

| Archivo | Qué hace |
|---|---|
| `bot.py` | Telegram (long polling): comandos, botones, guardar movimientos, cuentas, deudas, pagos, ahorro al cobrar, `/excel` |
| `formularios.py` | Formularios paso a paso (gasto, ingreso, ahorro, inversión) como los Google Forms de 2025; en gasto con banco pregunta crédito o débito |
| `lector.py` | Anotación rápida en texto libre (`45 almuerzo falabella credito`) |
| `categorias.py` | Categorías, medios de pago, tarjetas, alias (`cmr`→Falabella, `tinkoff`→T-Bank), Plin/Yape → banco |
| `finanzas.py` | Cálculos: tipo de cambio (automático del día, o fijo con `/tc`), soles/dólares/rublos, resúmenes, presupuesto, patrimonio, cuentas, deudas, metas, consejos |
| `informes.py` | Textos de resúmenes, deudas, patrimonio, metas; guarda Resúmenes en Notion |
| `excel.py` | Excel con un gráfico por hoja (el plan gratis de Notion permite un solo gráfico) |
| `notion.py` | Cliente REST de Notion y esquema de las bases; `setup_notion.py` crea o completa columnas |
| `resumen.py` | Resumen diario/semanal/mensual (timers de systemd) |
| `deploy/` | `instalar-todo.sh`, `actualizar.sh`, `auto-actualizar.sh` + timers (`finanzas-autoupdate` baja de GitHub cada 5 min) |

## Notion (página "💰 Finanzas")

Bases que usa el bot: **Movimientos, Presupuesto, Patrimonio, Metas, Resúmenes, Deudas**. Se buscan por título
debajo de la página padre (`NOTION_PARENT_PAGE_ID`).

- Deudas y Patrimonio se pueden editar a mano: manda `Saldo`/`Valor` + `Moneda`; las columnas en S/, USD y RUB
  las recalcula el bot.
- "🗄️ Archivo hasta el 30/09/2026" guarda lo anterior (Historial 2025, deudas, metas y presupuesto viejos).
  El bot **no** lo cuenta. El sistema empezó de cero el 01/10/2026.
- Una cuenta de Patrimonio se reconoce por banco + moneda (medio Interbank + USD → "Interbank dólares").
  Ingreso suma, gasto con débito resta, gasto a crédito va a la deuda de la tarjeta (Falabella → "Banco Falabella").

## Servidor

Ubuntu, el mismo de los bots de música (Core Forever). Código en `/opt/finanzas`, servicio `finanzas-bot`.
Actualizar a mano desde la Mac:

```bash
ssh root@TU-SERVIDOR 'cd /opt/finanzas && git pull -q origin main && bash deploy/actualizar.sh'
```

Después de correr eso una vez, el timer `finanzas-autoupdate` actualiza solo cada 5 minutos.

## Cuentas, efectivo y billeteras

- **🏧 Retirar efectivo** (`/retirar`): baja la cuenta del banco y sube "Efectivo" / "Efectivo dólares" /
  "Efectivo rublos" (se crea sola). No es gasto. Un gasto con medio Efectivo descuenta de ahí.
- **Plin** descuenta de Interbank y **Yape** de BCP (`C.BILLETERA_BANCO`). Debajo de un gasto con Yape sale
  el botón "🔁 Salió de Interbank" (`C.BILLETERA_OTROS`) para mover el descuento.

## Nube

El usuario pidió (2026-10-02) no gastar créditos de la nube en otra cosa que finanzas: las 5 tareas
programadas de música (noticias, cumpleaños, aniversarios) quedaron **apagadas**, no borradas. Música y
salud se trabajan en su sesión local de core-forever. La sesión "Daria proyecto" sí sigue en la nube.

## Pendiente

- Confirmar que el servidor ya corrió la actualización (el usuario dijo que actualizaría al final).
  Probar en Telegram: `/start`, `/deudas` con botones de pagar, `/gasto` con Falabella (pregunta crédito o débito), `/tc`, `/excel`.
- Faltan datos del usuario: día de pago de SIP y tasas de interés de SIP y Falabella.
- El tipo de cambio automático no se pudo probar contra internet real (la sesión en la nube no tenía red).
