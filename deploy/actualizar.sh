#!/bin/bash
# En el servidor: trae lo ultimo de GitHub, instala dependencias, corre los tests y reinicia.
#   ssh root@TU-SERVIDOR 'bash /opt/finanzas/deploy/actualizar.sh'
#
# Dos fases, como auto-actualizar.sh: el pull reescribe este archivo mientras bash lo lee.
set -e
. "$(dirname "$0")/comun.sh"
cd "$DIR"

if [ "$1" != "--ya-bajado" ]; then
  git pull -q origin main
  exec bash deploy/actualizar.sh --ya-bajado
fi

# El bot puede quedar apagado para siempre si salio con un codigo que systemd no reinicia
# (2: token malo, 3: otra copia leyendo la cola). Hay que comprobar que quedo arriba y, si no,
# limpiar el estado "failed" y levantarlo otra vez.
levantar_bot() {
  systemctl restart $SERVICIO-bot
  sleep 5
  for i in 1 2 3; do
    systemctl is-active -q $SERVICIO-bot && return 0
    echo "El bot no quedo arriba (intento $i):"
    journalctl -u $SERVICIO-bot --no-pager -n 5 -o cat
    systemctl reset-failed $SERVICIO-bot
    systemctl start $SERVICIO-bot
    sleep 15
  done
  systemctl is-active -q $SERVICIO-bot || { echo ">> EL BOT SIGUE CAIDO"; return 1; }
}

.venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m unittest discover -s tests -t . -q || echo ">> OJO: fallaron tests"
sudo -u "$SERVICIO" .venv/bin/python setup_notion.py >/dev/null   # agrega columnas nuevas si las hay
bash deploy/poner-timers.sh
systemctl enable -q --now $SERVICIO-avisos.timer   # recordatorios de cada mañana
systemctl enable -q --now $SERVICIO-vigia.timer    # si el bot se cae, lo levanta y avisa
systemctl enable -q --now $SERVICIO-autoupdate.timer   # desde ahora se actualiza solo cada 5 minutos
levantar_bot
journalctl -u $SERVICIO-bot --no-pager -n 3 -o cat
