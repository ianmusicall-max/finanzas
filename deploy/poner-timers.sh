#!/usr/bin/env bash
# Instala los servicios y timers de ESTA instalacion en systemd.
#
# Los archivos del repo dicen "finanzas", /opt/finanzas y America/Lima porque es el sistema
# original. Aca se copian cambiando el prefijo, la carpeta, el usuario y la zona por los de este
# .env, asi dos personas pueden tener cada una los suyos sin pisarse.
set -euo pipefail
. "$(dirname "$0")/comun.sh"
for origen in "$DIR"/deploy/systemd/finanzas-*; do
  destino="/etc/systemd/system/$SERVICIO-$(basename "$origen" | sed 's/^finanzas-//')"
  sed -e "s|/opt/finanzas|$DIR|g" \
      -e "s|^User=finanzas$|User=$SERVICIO|" \
      -e "s|^Group=finanzas$|Group=$SERVICIO|" \
      -e "s|finanzas-|$SERVICIO-|g" \
      -e "s|America/Lima|$ZONA|g" "$origen" > "$destino"
done
systemctl daemon-reload
