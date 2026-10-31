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
| `reloj.py` | `/reloj`: cronómetro de una tarea con tope, alarmas por Telegram y promedios |
| `deploy/` | `instalar-todo.sh`, `actualizar.sh`, `auto-actualizar.sh`, `vigia.sh` + timers (`finanzas-autoupdate` baja de GitHub cada 5 min; `finanzas-vigia` levanta el bot si se cayó y avisa) |

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
  compra en cuotas cae en el mes verdadero. Se pone con `/corte Falabella <día>`.
  **Falabella cargado el 14/10/2026: corte el 4, pago el 30** (período de facturación 04/09 → 04/10, vence
  30/10). **Sip (ex OH) cargado el 21/10/2026: corte el 8, pago el 5** (período 09/09 → 08/10, vence
  05/11; el pago del mes es igual al pago mínimo, que es lo que pasa cuando todo está en cuotas). Falta solo el corte del T-Bank: BBVA y Scotiabank
  quedaron fuera (el 21/10/2026 el usuario confirmó que BBVA está en cero sin deuda y que la cuenta
  de Scotiabank ya no existe), y la AFP tampoco existe.
- **El `Saldo` de una tarjeta es la deuda TOTAL, no el estado de cuenta** (14/10/2026). El saldo de
  "Banco Falabella" estaba inflado en casi un tercio: el monto que el usuario cargó a mano el 01/10 no
  era la deuda facturada, y encima el bot le sumó compras que ya estaban dentro de ese estado de cuenta,
  así que se contaron dos veces. Se reconstruyó sumando lo facturado al corte más las compras
  posteriores al corte. Eso también estaba hundiendo el patrimonio neto y desordenando `plan_deudas`.
  (Los montos de ese arreglo estaban escritos acá y se quitaron el 21/10/2026: el repo es público y la
  regla de arriba dice que no van montos reales. Siguen en el historial de git.)
  **Al cargar una tarjeta a mano**: va la deuda total de la app del banco, nunca el "pago total del mes" del
  estado de cuenta (ese es solo el ciclo cerrado) ni la línea utilizada. Después el bot la mantiene solo.
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

## El vigía: el bot no puede quedarse apagado en silencio (09/10/2026)

`finanzas-vigia.timer` corre `deploy/vigia.sh` cada 5 minutos. Si `finanzas-bot` no está activo:
`reset-failed`, `start`, y **avisa por Telegram** si lo levantó o si no pudo (con el espacio libre en
disco, que es una de las causas). Un aviso por hora como máximo (`/run/finanzas-vigia.ultimo`), porque si el
bot está en bucle esto corre cada 5 minutos.

Corre como root (usa `systemctl`) y manda el mensaje como el usuario `finanzas`. Mandar un mensaje no choca
con el `getUpdates` del bot aunque compartan token.

**Por qué hizo falta**: el usuario descubría que el bot estaba muerto escribiéndole y no recibiendo nada, y
desde la nube no hay forma de entrar al servidor (no hay cliente SSH ni llaves, y la red bloquea el 22), así
que la única salida era pedirle comandos por Terminal. Ahora el servidor se arregla solo y avisa.

## Un reinicio no puede dejar el bot apagado (09/10/2026)

**Esto tuvo el bot caído y mudo.** `finanzas-bot.service` tiene `RestartPreventExitStatus=2 3`, y el bot
salía con **3** en cuanto Telegram contestaba **409**. Pero el 409 es justo lo que contesta al reiniciar:
Telegram da por viva unos segundos la consulta `getUpdates` de la copia anterior. Resultado: `systemctl
restart` (que corre en cada actualización) tenía una carrera que mataba el bot **para siempre**, porque
systemd tiene prohibido reiniciarlo con ese código. Como se mergearon varios cambios seguidos, pasó.

Ahora el 409 se espera (`ESPERA_409`, `CONFLICTOS_409`: ~90 s de reintentos) y solo se sale con 3 si después
de eso sigue en conflicto, que ya es otra copia de verdad. El candado de archivo también espera
(`turno_del_bot(ESPERA_CANDADO)`) en vez de rendirse al instante. Lo cubre `tests.test_bot.Reinicio`.

Y los dos scripts de deploy comprueban que el bot quedó arriba (`levantar_bot`): si no, `reset-failed` y a
levantarlo de nuevo, hasta 3 veces. **Antes nadie se enteraba de que había quedado apagado.**

Los scripts van en **dos fases** (`--ya-bajado`): el `git pull`/`merge` reescribe el propio script mientras
bash lo está leyendo, así que la fase 1 baja los cambios y le pasa la posta con `exec` a la versión nueva.

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

## Renombrar una categoría sin desconectar Notion (13/10/2026)

"Comida y restaurantes" → **Restaurantes y cafés**, "Chatarra y golosinas" → **Golosinas**. Las filas que ya
están en Notion guardan el nombre viejo, así que renombrar la clave de `C.GASTOS` partiría cada categoría en
dos líneas y dejaría huérfana su fila de Presupuesto. Por eso el cambio va con un puente:

- `C.RENOMBRADAS` (viejo → nuevo) y `C.vigente()`, que se aplica **al leer** la columna `Categoría` de Notion
  (`F.movimientos`, `F.buscar`, `F.movimiento`, `F.presupuesto`, `F.compras_en_cuotas`).
- `C.anteriores()` + `F.fijar_presupuesto`: si la fila de Presupuesto todavía tiene el nombre viejo, se le
  cambia el nombre en vez de crear una repetida.
- `C.buscar_categoria` acepta el nombre viejo escrito a mano, y "comida" quedó como palabra clave de
  Restaurantes y cafés (`/presupuesto comida 800` y `45 comida` seguían dependiendo del nombre).

Lo cubre `tests.test_finanzas.CategoriasRenombradas`. **Al renombrar otra categoría, el camino es el mismo**:
agregarla a `RENOMBRADAS` y revisar que ninguna palabra clave viviera solo en el nombre viejo.

## La Tarjeta OH es la tarjeta Sip: eran un solo producto (21/10/2026)

El banco (InFinance XP S.A.) renombró la **Tarjeta OH** a **Sip**. El usuario lo confirmó: "SIP es
ex OH". El código creía que eran dos tarjetas distintas y eso **hacía perder plata de vista**:

| medio | iba a la deuda | existe en Notion |
|---|---|---|
| `Tarjeta OH` | `Tarjeta OH` | no |
| `SIP` | `Tarjeta SIP` (el fallback `"Tarjeta " + medio`) | no |

La fila real se llama **"Banco SIP"**, así que `F.compras_en_cuotas` (`finanzas.py`, vía
`C.deuda_de_tarjeta`) mandaba cada compra a crédito de esa tarjeta a una deuda fantasma en vez de
sumarla. Arreglado: `DEUDA_TARJETA` y `BANCO_TARJETA` llevan **las dos** formas a `"Banco SIP"`
(`Tarjeta OH` se dejó apuntando ahí para los movimientos ya guardados), `"Tarjeta OH"` salió de
`MEDIOS` y `TARJETAS` para que no se pueda volver a elegir, y el alias `oh` ahora da `SIP`.
Lo cubre `tests.test_categorias.TarjetaOhEsSip`.

En Notion la fila "Banco SIP" pasó de **Préstamo** a **Tarjeta de crédito**, con corte 8, pago 5 y
y la cuota del estado de cuenta (la que estaba no venía de ninguno). **El `Saldo` no se tocó**: el
pago del mes es el ciclo facturado, no la deuda total — la misma regla del Falabella. Y el recordatorio pasó de "Cuota Banco SIP, día 30" a "Pagar tarjeta Sip (ex
OH), día 5", con el monto del estado de cuenta.

**Esto también resolvió la duda vieja de las "12 cuotas desde el 5 de noviembre"**: eran de esta
tarjeta, no del préstamo. El 5 de noviembre es justo su día de pago, y que el pago mínimo sea igual
al total es lo que pasa cuando todo el saldo está en cuotas.

## Reloj de trabajo: `/reloj` (21/10/2026)

Cronometra una tarea con nombre, avisa al llegar a un tope y guarda cuánto tomó para dar el
promedio. Nació para medir las publicaciones de Facebook y no pasarse de hora.

- **No hay timer nuevo.** El bot ya espera a Telegram con `getUpdates(timeout=30)`; ese rato muerto
  es el que manda las alarmas (`Bot._avisar_reloj` → `R.vencidos()`, en el bucle de `correr`). Por
  eso una alarma puede llegar con hasta ~30 s de atraso.
- **Avisa dos veces y se calla**: al llegar al tope y otra vez al 50% pasado (`RECORDAR`). Un aviso
  que se repite para siempre se vuelve ruido y se empieza a ignorar.
- El estado va a `data/reloj.json` y **nada vive en memoria**: cada llamada lee el archivo, porque
  `finanzas-autoupdate` reinicia el bot cada vez que hay algo nuevo en `main`.
- **No va a Notion.** Los pomodoros no son finanzas y era una base menos que mantener. Si el usuario
  pide el conteo semanal, el camino es una base nueva, no meterlo en Movimientos.
- Los nombres se comparan en minúsculas y sin espacios de más (`_clave`), así que "Facebook" y
  "  facebook " son la misma tarea.
- **Se entra por botones** (`RELOJ_TOPES`): una grilla de 15 min a 8 horas, más **✏️ Otro** y sin
  tope. Se toca uno y el bot pregunta el nombre de la tarea. "Otro" agrega un paso antes (el tope lo
  escribe el usuario), por eso `pendiente` tiene un campo `paso` y el texto entra por `con_texto`,
  que atiende los dos pasos. `_minutos_de` entiende "90", "2 horas", "1h30" y "1.5 h", y rechaza
  cualquier cosa fuera de 1 min … `TOPE_MAX` (un día), que sería un error de tecleo. Ese "estoy esperando el nombre" **también va a disco**
  (`pendiente` en `reloj.json`), por lo mismo que los formularios; y se descarta si es de otro día,
  para que no revi­va al día siguiente y se coma un gasto.
- **`tests/test_bot.Base` tiene que apuntar `reloj.DATA` y `reloj.ESTADO` a un temporal**: el bot
  llama a `R.esperando(chat)` en *cada* mensaje de texto, así que sin eso los tests del bot leerían
  y escribirían el `data/reloj.json` real.
- El riesgo de esta pantalla es que lo que el usuario escriba mientras se le pide el nombre termine
  anotado como un gasto. Lo cubre
  `tests.test_bot.RelojPorBotones.test_el_nombre_arranca_el_bloque_y_no_se_anota_como_gasto`.

Lo cubre `tests.test_reloj`, que apunta `reloj.DATA`/`reloj.ESTADO` a un temporal y le cambia
`reloj.ahora` por un reloj falso (si no, los tests esperarían de verdad).

## Perfiles: el mismo código para dos personas (30/10/2026)

El usuario está clonando el sistema para **Дарья** (Moscú, rublos, sin deudas, todas sus tarjetas
de débito). Las categorías y los bancos son datos personales, así que vivían en `categorias.py` y
no se podían compartir. Ahora:

- `categorias.py` tiene **solo la lógica** (`normal`, `buscar_categoria`, `buscar_medio`,
  `vigente`, `deuda_de_tarjeta`…) y lo **estructural**: `TIPOS`, `GRUPOS`, `CUENTAS`, `ACTIVOS`,
  `PASIVOS`, `LIQUIDOS`. Eso último son llaves que el código usa y guarda en Notion tal cual, así
  que **no son cosa de cada perfil**.
- `perfiles/<nombre>.py` tiene los datos personales. Se elige con `PERFIL` en el `.env`
  (`PERFIL=jose` por defecto, así la instalación de siempre no cambia).
- `categorias.py` reexporta el perfil con `import *` **a propósito**: los diez módulos que hacen
  `import categorias as C` siguen usando `C.GASTOS`, `C.MEDIOS`… y no hubo que tocar ninguno.

**Dos cosas que estaban escritas a mano y le habrían roto el sistema a ella en silencio**:

- `finanzas.py` ponía `"Otros"` como respaldo cuando una fila de Notion viene sin categoría, en 3
  lugares. Para un perfil en ruso eso escribía una categoría inexistente. Ahora es `C.otros("Gasto")`,
  y cada perfil declara sus catch-all en `OTROS`.
- `bot.py` comparaba `mov.categoria != "Retiro de ahorro"` para no ofrecer apartar ahorro cuando el
  ingreso *es* un retiro del ahorro. En ruso nunca daba verdadero. Ahora es `C.RETIRO_AHORRO`.

`tests/test_perfiles.py` es un **contrato que corre sobre todos los perfiles**: que los catch-all de
`OTROS` existan de verdad, que `RETIRO_AHORRO` sea una categoría de ingreso, que las tarjetas y
billeteras estén en `MEDIOS`, que los alias apunten a medios que existen. Un perfil nuevo queda
cubierto por el solo hecho de existir — es lo que atrapa la clase de bug de arriba.

**Al agregar un perfil**: copiar uno existente, cambiar los datos, y correr los tests. Si algo no
cierra, el contrato lo dice por nombre.

### Lo que cambia de una persona a otra, todo en el `.env`

| Variable | Qué decide |
|---|---|
| `PERFIL` | Qué `perfiles/<nombre>.py` se carga: categorías, bancos, alias |
| `MONEDA_BASE` | El símbolo de las columnas de Notion (`columna()` en `config.py`): "Monto S/" o "Monto ₽". **Se define una vez, antes de `setup_notion.py`**: cambiarla después crea columnas nuevas y deja las viejas con los datos adentro |
| `ZONA_HORARIA` | El corte del día (`config.ahora()`) y la hora de los resúmenes |

**La moneda base** estaba escrita a mano en **68 lugares de 6 archivos**. Ahora sale de
`config.columna()`. Hay un test que recorre esos archivos buscando `"Monto S/"` literales: si
alguien vuelve a escribir la moneda a mano, el clon en rublos se rompería en silencio.

Al hacerlo, el primer intento llamó `col()` a la función y chocó con una variable de bucle llamada
`col` en `finanzas.py` (`UnboundLocalError` en 39 tests). Por eso se llama `columna()`.

**La zona horaria** no usa tzdata a propósito: ni Lima ni Moscú tienen horario de verano, así que
basta el desfase fijo (`config.ZONAS`). También acepta `UTC+3` o `-5` a mano, y si no entiende la
zona **no arranca** en vez de sacar los resúmenes a cualquier hora. Los `.timer` del repo dicen
`America/Lima`; `deploy/poner-timers.sh` los copia a systemd reemplazando esa cadena por lo que
diga `ZONA_HORARIA`, y lo llaman los tres scripts que instalaban los timers.

**`.env.example` tenía el `NOTION_PARENT_PAGE_ID` real de José** en un repo público, y un clon lo
habría copiado tal cual. Ahora es un hueco.

## Dos sistemas en el mismo servidor (31/10/2026)

El clon de Дарья vive en `/opt/daria`, en el mismo servidor que `/opt/finanzas`. Los servicios de
systemd son **globales**: si los dos se llamaran `finanzas-bot`, el segundo que se instale le pisa
el bot al primero. Por eso el prefijo sale de `SERVICIO` en el `.env` (por defecto `finanzas`, así
la instalación de siempre no cambia), y es también el **usuario del sistema**.

`deploy/poner-timers.sh` copia los units a systemd cambiando cuatro cosas: la carpeta
(`/opt/finanzas` → la real), el usuario (`User=`/`Group=`), el prefijo (`finanzas-` → `$SERVICIO-`)
y la zona (`America/Lima` → `ZONA_HORARIA`). `deploy/comun.sh` lee esos datos del `.env` y lo usan
los tres scripts de deploy, que ya no nombran "finanzas" a mano.

| | José | Дарья |
|---|---|---|
| Carpeta | `/opt/finanzas` | `/opt/daria` |
| Servicios | `finanzas-bot`, `finanzas-diario.timer`… | `daria-bot`, `daria-diario.timer`… |
| Usuario | `finanzas` | `daria` |
| Zona de los timers | America/Lima | Europe/Moscow |

Lo cubre `tests.test_perfiles.ServiciosDeSystemd`: que ninguna directiva de los units nombre el
sistema de una forma que el instalador no reemplace, y que el instalador siga tocando las cuatro.
**Al agregar un servicio nuevo**, el test avisa si quedó atado al sistema original.

## El menú y el idioma salen del perfil (31/10/2026)

A Дарья le aparecía el menú entero de José: 25 botones en español, con Deudas, Plan de deudas,
Patrimonio, Pagos y Proyección, que ella no usa porque no tiene deudas ni tarjetas de crédito ni
patrimonio. Se le habían personalizado los datos y no la interfaz.

- El **perfil** dice qué opciones ve (`MENU_OPCIONES`, por filas, con el nombre del comando).
- El **idioma** dice cómo se llaman (`idiomas/<IDIOMA>.py`, `IDIOMA` en el `.env`).
- `bot.MENU` se arma con los dos. Los comandos que no están en el menú **siguen existiendo**: el
  día que tenga una tarjeta de crédito se agrega `deudas` a su fila y ya funciona.

`bot.MENU` descarta en silencio una opción sin nombre, así que un botón mal escrito no aparecería
y nadie se enteraría: `tests.test_perfiles.MenuPorPerfil` comprueba que cada opción tenga nombre en
todos los idiomas y que los idiomas cubran las mismas claves.

**Falta**: los textos de adentro (preguntas de los formularios, confirmaciones, resúmenes) siguen
en español. Son ~1.200 entre `bot.py`, `formularios.py`, `informes.py` y `finanzas.py`.

## Todo en su idioma, Notion incluido (31/10/2026)

El menú ya salía en ruso, pero lo de adentro no: los formularios, la pantalla de inicio, cada
monto (en soles) y todo Notion seguían en español. Tres cosas escritas a mano eran **bugs
silenciosos** para ella, de la misma familia que el `"Otros"` de `finanzas.py`:

- Guardar un ahorro escribía en Notion `"Fondo de emergencia"` / `"Metas"` / `"Ahorro general"`,
  categorías que no existen en su base. Ahora lo decide `C.ahorro_de_meta()` con
  `AHORRO_EMERGENCIA` / `AHORRO_METAS` del perfil, reconociendo la reserva por las **palabras
  clave de `AHORROS`**, no por la palabra "emergencia".
- `"PEN"` suelto en ~20 sitios como moneda por defecto: cada fila de Notion sin moneda se leía
  como soles.
- `/start` proponía `/limite 1500 rub` a cualquiera. Ahora es `LIMITE_EJEMPLO` del perfil.

**Los textos** se traducen buscando el español, no con una clave inventada: `t("¿Qué fecha?")`.
Con claves el código deja de decir lo que sale en pantalla, y un error de tipeo muestra la clave
cruda. Así una frase sin traducir **sale en español en vez de romper el bot**, que es lo que
permite traducir de a poco — pero entonces el que se entera de lo que falta es quien usa el bot.
Por eso `tests/test_idiomas.py` lee todos los `t("...")` del repo y, si a un idioma le falta
alguno, **lo nombra entero**.

Al envolver los textos de `formularios.py`, la función `t()` chocó con una variable local `t`
(el texto que escribió la persona) en `_texto`. Es **exactamente el tropiezo de `col()` contra
`columna()`** de más arriba; se llama `escrito`, que además dice qué es.

**La moneda base** no era solo un símbolo: el tipo de cambio entero era "soles por unidad"
(`finanzas.soles`, `_descargar_tc`, `s()`, `s3()`). Ahora es "unidades de la `MONEDA_BASE` por
unidad", sale de `config.POR_USD` y `soles()` se llama **`en_base()`**, porque con la base en
rublos el nombre mentía. Los números de `POR_USD` están elegidos para que con base PEN den
exactamente los de siempre (3.75 / 4.10 / 0.045): la instalación de José no cambia en nada.
Las dos monedas que acompañan a cada monto las dice el perfil (`MONEDAS_RESUMEN`).

**Ojo con los `TC_USD` del `.env`**: significan "unidades de la base por dólar". Un `.env`
copiado de otra instalación los trae en la moneda de la otra y convierte mal todo sin avisar.
Por eso en `.env.example` quedaron comentados: sin ellos el sistema calcula unos razonables.

### Notion en el idioma de su dueño

Las bases, las columnas y los valores que son llaves del sistema se crean en el idioma del
`.env` (`NOTION_PROP` y `NOTION_VALOR` en `idiomas/<código>.py`). **El código los sigue nombrando
en español** (`f.get("Monto")`, `p_select("Gasto")`): traducir eso habrían sido cientos de
sitios. La traducción pasa **solo en la frontera**, en `notion.py`: `_esquema_a_notion`,
`_props_a_notion`, `_filtro_a_notion` y `fila()`. Ningún otro módulo cambió.

Lo delicado es **qué valores se traducen**. Solo los de `notion.COLUMNAS_LLAVE` (Tipo, Grupo,
Cuenta, Tarjeta, Frecuencia, Origen, Clase, Prioridad, Estado). Las categorías, los medios de
pago y las monedas quedan fuera **a propósito**: salen del perfil y ya vienen en su idioma, y
traducirlos los mezclaría — la cuenta `"Salud"` y la categoría `"Здоровье"` serían la misma
palabra, y al leer de Notion no se sabría cuál era. Por eso la traducción es **por columna**, y
hay un test de que ningún par de nombres se traduce igual (`test_la_vuelta_no_es_ambigua`).

Dos detalles que no se ven:
- El símbolo del final (`Monto ₽`, `Saldo USD`) no se traduce: `n_prop` lo separa y lo vuelve a
  pegar.
- La fórmula de Metas nombra columnas **dentro de un texto**, así que la traducción de las
  llaves no la alcanza: se escribe ya con `n_prop(columna("Objetivo"))`. Si no, Notion contesta
  "Type error with formula" y la base no se crea.

**Al agregar una columna o un valor nuevo**, `tests/test_idiomas.py` avisa por nombre si algún
idioma se quedó sin traducirlo.

**Falta**: los textos de `informes.py` y `finanzas.py` (resúmenes, consejos, plan de deudas) y
los meses abreviados de `excel.py` siguen en español.

## Los scripts de deploy nombraban "finanzas" a mano (31/10/2026)

Los `.sh` se copian tal cual a las dos instalaciones, así que un `/opt/finanzas` escrito a mano
hace que el sistema del segundo trabaje sobre el del primero. Había tres:

- `actualizar.sh` y `auto-actualizar.sh` hacían `cd /opt/finanzas` **después** de leer
  `comun.sh`. O sea: `daria-autoupdate.timer`, cada 5 minutos, hacía `git pull` y corría los
  tests **en la carpeta de José**, y después reiniciaba `daria-bot`. Encima
  `sudo -u daria .venv/bin/python setup_notion.py` salía desde ahí, con el `.env` equivocado.
- `vigia.sh` era peor: ni siquiera leía `comun.sh`. Vigilaba `finanzas-bot`, lo encontraba vivo
  y **salía sin mirar el bot que tenía que cuidar**. El bot de Дарья no tenía vigía, que es
  justo lo que el vigía existe para evitar.

Ahora todos leen `comun.sh` y usan `$DIR` y `$SERVICIO`. Lo cubre
`tests.test_perfiles.ScriptsDeDeploy`, que lee cada script y falla si una línea de código (no un
comentario) nombra la carpeta, el servicio o el usuario a mano. `poner-timers.sh` y los
instaladores quedan fuera: son los que hacen el reemplazo y los que dan el valor por defecto.

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
