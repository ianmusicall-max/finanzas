#!/bin/bash
# Instala o actualiza el bot de finanzas con una sola linea, en el servidor:
#   curl -sL https://raw.githubusercontent.com/ianmusicall-max/finanzas/main/deploy/instalar-todo.sh | bash
# Pide los dos tokens solo la primera vez. Tu ID de Telegram lo toma de Core Forever.
set -e
DIR=/opt/finanzas

if [ -d "$DIR/.git" ]; then
  echo ">> Ya estaba instalado: actualizo."
  exec bash "$DIR/deploy/actualizar.sh"
fi

rm -rf "$DIR"
git clone -q https://github.com/ianmusicall-max/finanzas "$DIR"
cd "$DIR"
cp .env.example .env

echo
echo "Pega cada token y pulsa Enter (no se ve mientras lo pegas, es normal)."
read -r -s -p "1) Token del bot de Telegram (de @BotFather): " TOK < /dev/tty; echo
read -r -s -p "2) Token de Notion (empieza con ntn_): " NT < /dev/tty; echo
TOK=$(echo "$TOK" | tr -d '[:space:]'); NT=$(echo "$NT" | tr -d '[:space:]')
if [ -z "$TOK" ] || [ -z "$NT" ]; then
  echo "Falta un token. Vuelve a pegar la linea de instalacion."; rm -rf "$DIR"; exit 1
fi

ID=""
for f in /opt/core-forever/.env /opt/nutricion/.env; do
  [ -z "$ID" ] && [ -f "$f" ] && ID=$(grep '^TELEGRAM_CHAT_ID=' "$f" | head -1 | cut -d= -f2- | tr -d '"'"'"' ')
done

sed -i "s|^TELEGRAM_TOKEN=.*|TELEGRAM_TOKEN=$TOK|; s|^NOTION_TOKEN=.*|NOTION_TOKEN=$NT|; s|^TELEGRAM_USUARIOS=.*|TELEGRAM_USUARIOS=$ID|" .env
unset TOK NT
[ -n "$ID" ] && echo ">> Tu ID de Telegram: $ID (el mismo de Core Forever)" || echo ">> No encontre tu ID: el bot te lo dira con /id"

bash deploy/instalar.sh
echo
echo "=========================================="
echo " LISTO. Escribele /start a tu bot en Telegram."
echo "=========================================="
