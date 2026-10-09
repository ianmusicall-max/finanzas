#!/bin/bash
# Lo corre finanzas-autoupdate.timer cada 5 minutos. Si hay cambios en GitHub los baja,
# corre los tests y reinicia el bot. Si un test falla, vuelve a la version anterior y no reinicia.
#   Ver lo que hizo:  journalctl -u finanzas-autoupdate --no-pager -n 20
#
# Va en dos fases porque el merge reescribe este mismo archivo mientras bash lo esta leyendo:
# la fase 1 baja los cambios y le pasa la posta a la version nueva del script.
set -e
cd /opt/finanzas

if [ "$1" != "--ya-bajado" ]; then
  git fetch -q origin main
  antes=$(git rev-parse HEAD)
  [ "$antes" = "$(git rev-parse origin/main)" ] && exit 0
  git merge -q --ff-only origin/main
  exec bash deploy/auto-actualizar.sh --ya-bajado "$antes"
fi
antes="$2"

# El bot puede quedar apagado para siempre si salio con un codigo que systemd no reinicia
# (2: token malo, 3: otra copia leyendo la cola). Hay que comprobar que quedo arriba y, si no,
# limpiar el estado "failed" y levantarlo otra vez.
levantar_bot() {
  systemctl restart finanzas-bot
  sleep 5
  for i in 1 2 3; do
    systemctl is-active -q finanzas-bot && return 0
    echo "El bot no quedo arriba (intento $i):"
    journalctl -u finanzas-bot --no-pager -n 5 -o cat
    systemctl reset-failed finanzas-bot
    systemctl start finanzas-bot
    sleep 15
  done
  systemctl is-active -q finanzas-bot || { echo ">> EL BOT SIGUE CAIDO"; return 1; }
}

.venv/bin/pip install -q -r requirements.txt
if ! .venv/bin/python -m unittest discover -s tests -t . -q; then
  echo "Fallaron los tests: vuelvo a ${antes:0:7} y el bot sigue como estaba."
  git reset -q --hard "$antes"
  exit 1
fi
sudo -u finanzas .venv/bin/python setup_notion.py >/dev/null   # agrega columnas nuevas si las hay
cp deploy/systemd/finanzas-* /etc/systemd/system/ && systemctl daemon-reload
systemctl enable -q --now finanzas-avisos.timer   # recordatorios de cada mañana
systemctl enable -q --now finanzas-vigia.timer    # si el bot se cae, lo levanta y avisa
levantar_bot
echo "Actualizado de ${antes:0:7} a $(git rev-parse --short HEAD)."
