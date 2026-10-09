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
| `formularios.py` | Formularios paso a paso (gasto, ingreso, ahorro, inversión) como los Google Forms de 2025; en gasto con tarjeta pregunta crédito o débito y en cuántas cuotas. **Ya no pregunta "¿A qué cuenta va?"** (Gastos/Salud/Inversión/Educación): se quitó el 09/10/2026 porque el usuario leía "cuenta" como *cuenta de banco* y esperaba elegir Interbank o BCP ahí. Ahora la primera pregunta es el banco. El estado se guarda en `data/formularios.json` para que un reinicio no corte el formulario |
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
- **Día de corte** (columna nueva en Deudas, 08/10/2026): con el corte y el `Día de pago` el bot sabe en qué
  estado de cuenta cae cada compra a crédito y cuándo se paga (`F.cuando_se_paga`), y la primera cuota de una
  compra en cuotas cae en el mes verdadero. Se pone con `/corte Falabella 10`. Falta cargar los cortes reales.
- **"Banco Falabella" es la tarjeta de crédito**, no el préstamo. El bot busca ese nombre exacto
  (`C.DEUDA_TARJETA`) para sumarle las compras a crédito, así que no se renombra. El préstamo quedó aparte
  como "Préstamo Falabella" (03/10/2026), porque las dos tenían tasas distintas y juntas no se podía decir
  cuál conviene pagar primero.

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
- **Plin** y **Yape** descuentan de Interbank (`C.BILLETERA_BANCO`; hasta el 08/10/2026 Yape descontaba de
  BCP, pero el usuario dijo que últimamente siempre yapea desde Interbank). Debajo de un gasto con Yape sale
  el botón "🔁 Salió de BCP" (`C.BILLETERA_OTROS`) para mover el descuento.

## Nube

El usuario pidió (2026-10-02) no gastar créditos de la nube en otra cosa que finanzas: las 5 tareas
programadas de música (noticias, cumpleaños, aniversarios) quedaron **apagadas**, no borradas. Música y
salud se trabajan en su sesión local de core-forever. La sesión "Daria proyecto" sí sigue en la nube.

## El bot se reinicia solo: nada importante puede vivir solo en memoria

`finanzas-autoupdate` reinicia `finanzas-bot` cada vez que hay algo nuevo en `main` (revisa cada 5 min), y
systemd lo reinicia si se cae. Eso rompió dos cosas y hay que tenerlo presente al agregar features:

- **Formularios** (09/10/2026): un `/gasto` a medio llenar se perdía y, al tocar el botón siguiente, el bot
  le quitaba los botones al mensaje y contestaba "ese formulario ya terminó": la pregunta quedaba muda y el
  usuario lo vivía como "se queda trabado en «¿A qué cuenta va?» y no aparece ninguna opción". Arreglado
  guardando el estado en `data/formularios.json` (`_cargar_estados` / `_guardar_estados`). Si igual se pierde,
  `Formularios.reempezar()` ofrece botones para arrancar de nuevo en vez de dejar un callejón sin salida.
- **Deshacer un movimiento** (08/10/2026): dependía de diccionarios en memoria; ahora los efectos se
  reconstruyen de la fila de Notion.

Lo que sigue en memoria y se pierde al reiniciar: `_metas_de` (a qué meta fue un ahorro), el retiro de
efectivo para deshacer, y el paso a paso de pagar una deuda o de dar de alta una suscripción. Si alguno
empieza a molestar, el camino es el mismo: a disco, con fecha para que no revivan al día siguiente.

Los tests tienen que aislar los archivos: `tests/test_bot.py` apunta `formularios.AJUSTES`, `formularios.DATA`
y `formularios.ESTADOS` a un temporal en `setUp`, o el estado se pasa de un test al siguiente.

## Pendiente

- ~~Confirmar que el servidor se actualiza solo~~: confirmado el 03/10/2026 (`/retirar` responde en Telegram,
  así que el timer `finanzas-autoupdate` está corriendo). Falta probar el resto: `/deudas` con botones de
  pagar, `/gasto` con Falabella (pregunta crédito o débito), `/tc`, `/excel`.
- ~~Faltan las tasas de interés~~: cargadas en Notion el 03/10/2026 (SIP y la tarjeta Falabella, las dos
  cerca del 79% anual; en Notion `Tasa anual` se guarda como decimal, 0.7899 → el bot muestra 79%).
  **Queda una duda sin resolver**: el usuario mencionó "12 cuotas desde el 5 de noviembre", pero los números
  de SIP no cuadran con 12 cuotas a esa tasa (saldría una cuota bastante más alta que la que figura). Hay que
  preguntarle de qué préstamo era y cuál es la cuota verdadera.
- ~~La tarjeta Falabella no tiene `Cuota mensual`~~: desde el 08/10/2026 la cuota de una tarjeta la calcula
  `F.deudas()` sumando las compras en cuotas (`F.compras_en_cuotas`, columna `Cuotas` de Movimientos). **No se
  escribe en Notion**: `Cuota mensual` sigue siendo del usuario y se usa cuando esa deuda no tiene compras en
  cuotas (por ejemplo el préstamo SIP). Si el usuario quiere un monto fijo para la tarjeta igual, va ahí.
- El tipo de cambio automático sigue sin probarse **bajando datos reales**: la política de red de la sesión
  en la nube deniega `open.er-api.com` y `cdn.jsdelivr.net` (403 del proxy). Lo que sí quedó probado contra
  una caída de red real: usa el respaldo del `.env`, no reintenta antes de 30 min, `/tc` a mano funciona y
  nada explota. Para probarlo de verdad hay que mirar `/tc` en Telegram contra el servidor.
