#!/bin/bash
# Lo corre $SERVICIO-vigia.timer cada 5 minutos. Si el bot esta caido lo levanta y AVISA por
# Telegram, para que nadie tenga que descubrirlo escribiendole al bot y no recibir nada.
#
# Hizo falta porque el bot podia quedar apagado en silencio: salia con un codigo que systemd
# tiene prohibido reiniciar (RestartPreventExitStatus=2 3), o se queda sin disco al arrancar.
#   Ver lo que hizo:  journalctl -u $SERVICIO-vigia --no-pager -n 20
#
# Lee comun.sh igual que los demas scripts de deploy. Sin eso vigilaba "finanzas-bot" desde
# cualquier instalacion: el vigia del segundo sistema miraba el bot del primero y, como ese
# estaba arriba, salia contento sin mirar el suyo. Un bot sin vigia y nadie enterandose.
set -u
. "$(dirname "$0")/comun.sh"
cd "$DIR" || exit 0

systemctl is-active -q $SERVICIO-bot && exit 0

echo "El bot no esta activo. Ultimas lineas antes de levantarlo:"
journalctl -u $SERVICIO-bot --no-pager -n 15 -o cat
libre=$(df -h / | awk 'NR==2 {print $4" libres de "$2}')

systemctl reset-failed $SERVICIO-bot 2>/dev/null
systemctl start $SERVICIO-bot
sleep 10

if systemctl is-active -q $SERVICIO-bot; then
  aviso="⚠️ El bot se había apagado y lo levanté solo. Ya podés seguir usándolo."
  echo "Levantado."
else
  aviso="🔴 El bot se apagó y no pude levantarlo. Disco: $libre. Hay que entrar al servidor."
  echo "No pude levantarlo."
fi

# Si el bot esta en bucle, esto corre cada 5 minutos: un aviso por hora alcanza y sobra.
SELLO=/run/$SERVICIO-vigia.ultimo
ahora=$(date +%s)
if [ $(( ahora - $(cat "$SELLO" 2>/dev/null || echo 0) )) -lt 3600 ]; then
  echo "Ya avisé hace menos de una hora; no repito."
  exit 0
fi
echo "$ahora" > "$SELLO" 2>/dev/null

# Mandar un mensaje no choca con la cola del bot, aunque usen el mismo token.
sudo -u "$SERVICIO" .venv/bin/python - "$aviso" <<'PY'
import sys
from config import TELEGRAM_USUARIOS
from telegram import Telegram
try:
    tg = Telegram()
    for u in TELEGRAM_USUARIOS:
        tg.enviar(u, sys.argv[1])
    print("Avisado a %d usuario(s)." % len(TELEGRAM_USUARIOS))
except Exception as exc:
    print("  [vigia] no pude avisar: %s: %s" % (type(exc).__name__, exc))
PY
