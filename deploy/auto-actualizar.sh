#!/bin/bash
# Lo corre finanzas-autoupdate.timer cada 5 minutos. Si hay cambios en GitHub los baja,
# corre los tests y reinicia el bot. Si un test falla, vuelve a la version anterior y no reinicia.
#   Ver lo que hizo:  journalctl -u finanzas-autoupdate --no-pager -n 20
set -e
cd /opt/finanzas
git fetch -q origin main
antes=$(git rev-parse HEAD)
[ "$antes" = "$(git rev-parse origin/main)" ] && exit 0
git merge -q --ff-only origin/main
.venv/bin/pip install -q -r requirements.txt
if ! .venv/bin/python -m unittest discover -s tests -t . -q; then
  echo "Fallaron los tests: vuelvo a ${antes:0:7} y el bot sigue como estaba."
  git reset -q --hard "$antes"
  exit 1
fi
sudo -u finanzas .venv/bin/python setup_notion.py >/dev/null   # agrega columnas nuevas si las hay
cp deploy/systemd/finanzas-* /etc/systemd/system/ && systemctl daemon-reload
systemctl enable -q --now finanzas-avisos.timer   # recordatorios de cada mañana
systemctl restart finanzas-bot
echo "Actualizado de ${antes:0:7} a $(git rev-parse --short HEAD)."
