#!/usr/bin/env python3
"""Autoriza Google Calendar una vez desde la Mac, sin dependencias nuevas.

.venv/bin/python setup_google_calendar.py --cliente ~/Downloads/cliente.json --chat TU_ID
Después copia data/google_calendar.json al data/ del bot (usuario del servicio).
"""
import argparse
import base64
import hashlib
import json
import os
import secrets
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import requests

SCOPE = 'https://www.googleapis.com/auth/calendar.events.owned'


def autorizar(cliente, chat, destino, calendario='primary'):
    config = json.loads(Path(cliente).expanduser().read_text()).get('installed')
    if not config or not all(config.get(k) for k in ('client_id', 'client_secret')):
        raise ValueError('Descarga un cliente OAuth de tipo Aplicación de escritorio desde Google Cloud.')
    estado = secrets.token_urlsafe(32)
    verificador = secrets.token_urlsafe(64)
    reto = base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest()).rstrip(b'=').decode()
    resultado = {}

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # no registrar el código OAuth

        def do_GET(self):
            u = urlsplit(self.path)
            q = parse_qs(u.query)
            if u.path != '/callback' or q.get('state') != [estado]:
                self.send_error(400, 'Respuesta no valida')
                return
            resultado.update(q)
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write('Puedes cerrar esta ventana y volver a la Terminal.'.encode())

    with HTTPServer(('127.0.0.1', 0), Callback) as servidor:
        redirect = 'http://127.0.0.1:%d/callback' % servidor.server_port
        url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
            'client_id': config['client_id'], 'redirect_uri': redirect,
            'response_type': 'code', 'scope': SCOPE, 'state': estado,
            'code_challenge': reto, 'code_challenge_method': 'S256',
            'access_type': 'offline', 'prompt': 'consent'})
        print('Abre este enlace en el navegador de esta Mac y autoriza tu cuenta:\n' + url, flush=True)
        servidor.timeout = 1
        limite = time.monotonic() + 600
        while not resultado and time.monotonic() < limite:
            servidor.handle_request()
    if not resultado.get('code'):
        raise ValueError('La autorización fue cancelada o expiró. Puedes volver a intentarlo.')
    r = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': config['client_id'], 'client_secret': config['client_secret'],
        'code': resultado['code'][0], 'redirect_uri': redirect,
        'code_verifier': verificador, 'grant_type': 'authorization_code'}, timeout=30)
    if not r.ok or not r.json().get('refresh_token'):
        raise ValueError('Google no entregó autorización permanente. Revisa las credenciales y vuelve a intentarlo.')
    datos = {'client_id': config['client_id'], 'client_secret': config['client_secret'],
             'refresh_token': r.json()['refresh_token'], 'chat': str(chat), 'calendar_id': calendario}
    destino = Path(destino).expanduser()
    destino.parent.mkdir(parents=True, exist_ok=True)
    with os.fdopen(os.open(str(destino), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as f:
        json.dump(datos, f)
    os.chmod(destino, 0o600)
    print('Autorización guardada. Copia este archivo privado al servidor: %s' % destino)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cliente', required=True)
    ap.add_argument('--chat', required=True, type=int)
    ap.add_argument('--salida', default='data/google_calendar.json')
    ap.add_argument('--calendario', default='primary')
    a = ap.parse_args()
    try:
        autorizar(a.cliente, a.chat, a.salida, a.calendario)
    except (OSError, ValueError, requests.RequestException):
        print('No se pudo completar la conexión. Revisa el archivo del cliente, la red y la autorización de Google.')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
