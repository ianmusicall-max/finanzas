#!/usr/bin/env bash
# Copia los timers a systemd y les pone la zona horaria del .env.
#
# Los .timer del repo dicen "America/Lima" porque es el sistema original. Un clon en otra ciudad
# (Moscu) necesita que los resumenes salgan a SU hora, asi que al instalarlos se reemplaza por lo
# que diga ZONA_HORARIA. Si no esta, queda Lima y nada cambia.
set -euo pipefail
cp deploy/systemd/finanzas-* /etc/systemd/system/
ZH=$(sed -n 's/^ZONA_HORARIA=//p' .env 2>/dev/null | tr -d " \"'" | head -1)
sed -i "s|America/Lima|${ZH:-America/Lima}|g" /etc/systemd/system/finanzas-*.timer
systemctl daemon-reload
