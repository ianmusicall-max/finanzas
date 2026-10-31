# Datos de ESTA instalacion, para que dos sistemas convivan en el mismo servidor.
#
# Los servicios de systemd son globales: si el de Дарья se llamara igual que el de José, el
# segundo que se instale pisa al primero y uno de los dos se queda sin bot. Por eso el prefijo
# (y el usuario del sistema) salen de SERVICIO en el .env, que por defecto es "finanzas" para
# no cambiar nada de la instalacion de siempre.
DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
_leer() { sed -n "s/^$1=//p" "$DIR/.env" 2>/dev/null | tr -d " \"'" | head -1; }
SERVICIO=$(_leer SERVICIO); SERVICIO=${SERVICIO:-finanzas}
ZONA=$(_leer ZONA_HORARIA); ZONA=${ZONA:-America/Lima}
