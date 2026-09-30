#!/bin/bash
# En el servidor: trae lo ultimo de GitHub, instala dependencias, corre los tests y reinicia.
#   ssh root@67.205.160.34 'bash /opt/finanzas/deploy/actualizar.sh'
set -e
cd /opt/finanzas && git pull -q origin main
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m unittest discover -s tests -t . -q || echo ">> OJO: fallaron tests"
sudo -u finanzas .venv/bin/python setup_notion.py >/dev/null   # agrega columnas nuevas si las hay
cp deploy/systemd/finanzas-* /etc/systemd/system/ && systemctl daemon-reload
systemctl restart finanzas-bot
sleep 3
systemctl is-active finanzas-bot
journalctl -u finanzas-bot --no-pager -n 3 -o cat
