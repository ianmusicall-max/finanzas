#!/bin/bash
# Primera instalacion en el servidor (el mismo de Core Forever). Correr como root:
#   git clone https://github.com/ianmusicall-max/finanzas /opt/finanzas
#   bash /opt/finanzas/deploy/instalar.sh
set -e
. "$(dirname "$0")/comun.sh"
cd "$DIR"
id "$SERVICIO" >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin "$SERVICIO"
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
mkdir -p data
[ -f .env ] || { cp .env.example .env; echo ">> Completa $DIR/.env y vuelve a correr este script."; exit 1; }
chown -R "$SERVICIO:$SERVICIO" data
chmod 600 .env && chown "$SERVICIO:$SERVICIO" .env
.venv/bin/python -m unittest discover -s tests -t . -q
sudo -u "$SERVICIO" .venv/bin/python setup_notion.py
bash deploy/poner-timers.sh
systemctl daemon-reload
systemctl enable --now $SERVICIO-bot $SERVICIO-diario.timer $SERVICIO-semanal.timer $SERVICIO-mensual.timer $SERVICIO-autoupdate.timer $SERVICIO-avisos.timer
sleep 3
systemctl is-active $SERVICIO-bot
systemctl list-timers "$SERVICIO-*" --no-pager
