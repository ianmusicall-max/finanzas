#!/bin/bash
# Primera instalacion en el servidor (el mismo de Core Forever). Correr como root:
#   git clone https://github.com/ianmusicall-max/finanzas /opt/finanzas
#   bash /opt/finanzas/deploy/instalar.sh
set -e
cd /opt/finanzas
id finanzas >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin finanzas
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
mkdir -p data
[ -f .env ] || { cp .env.example .env; echo ">> Completa /opt/finanzas/.env y vuelve a correr este script."; exit 1; }
chown -R finanzas:finanzas data
chmod 600 .env && chown finanzas:finanzas .env
.venv/bin/python -m unittest discover -s tests -t . -q
sudo -u finanzas .venv/bin/python setup_notion.py
cp deploy/systemd/finanzas-* /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now finanzas-bot finanzas-diario.timer finanzas-semanal.timer finanzas-mensual.timer
sleep 3
systemctl is-active finanzas-bot
systemctl list-timers 'finanzas-*' --no-pager
