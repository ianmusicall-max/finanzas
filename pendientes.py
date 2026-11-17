"""Lista de tareas persistente por chat y exportación a Google Calendar."""
import fcntl
import json
import os
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from html import escape
from urllib.parse import quote

import requests

from config import DATA, hoy

ESTADO = DATA / 'pendientes.json'
GOOGLE = DATA / 'google_calendar.json'


@contextmanager
def estado():
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    with ESTADO.with_suffix('.lock').open('a') as candado:
        fcntl.flock(candado, fcntl.LOCK_EX)
        try:
            datos = json.loads(ESTADO.read_text()) if ESTADO.exists() else {}
            yield datos
            temporal = ESTADO.with_suffix('.tmp')
            temporal.write_text(json.dumps(datos, ensure_ascii=False))
            os.chmod(temporal, 0o600)
            temporal.replace(ESTADO)
        finally:
            fcntl.flock(candado, fcntl.LOCK_UN)


def _chat(datos, chat):
    c = datos.setdefault(str(chat), {'tareas': [], 'paso': None})
    if c['paso'] and c['paso'].get('creado') != hoy().isoformat():
        c['paso'] = None
    return c


def lista(chat, hechas=False):
    with estado() as datos:
        tareas = _chat(datos, chat)['tareas']
        return sorted([dict(x) for x in tareas if x['hecha'] == hechas],
                      key=lambda x: (x['fecha'] or '9999', x['id']))


def esperando(chat):
    with estado() as datos:
        return bool(_chat(datos, chat)['paso'])


def empezar(chat):
    with estado() as datos:
        _chat(datos, chat)['paso'] = {'tipo': 'titulo', 'creado': hoy().isoformat()}
    return '📝 Escribe una tarea o varias, una por línea (hasta 20).', [[('✖️ Cancelar', 'pd:cancelar')]]


def cancelar(chat):
    with estado() as datos:
        _chat(datos, chat)['paso'] = None


def opciones_fecha():
    return [[('Hoy', 'pd:fecha:hoy'), ('Mañana', 'pd:fecha:manana')],
            [('En una semana', 'pd:fecha:semana'), ('📅 Otra fecha', 'pd:fecha:otra')],
            [('📥 Sin fecha', 'pd:fecha:ninguna'), ('✖️ Cancelar', 'pd:cancelar')]]


def con_texto(chat, texto):
    with estado() as datos:
        c = _chat(datos, chat)
        paso = c['paso']
        if not paso:
            return 'Abre /pendientes para agregar una tarea.', None
        if paso['tipo'] == 'titulo':
            titulos = [x.strip() for x in texto.splitlines() if x.strip()]
            if not titulos or len(titulos) > 20 or any(len(x) > 200 for x in titulos):
                return 'Escribe de 1 a 20 tareas, de hasta 200 caracteres cada una.', None
            c['paso'] = {'tipo': 'fecha', 'titulos': titulos, 'creado': hoy().isoformat()}
            return '📅 ¿Qué fecha límite les ponemos?', opciones_fecha()
        try:
            fecha = date.fromisoformat(texto) if '-' in texto else datetime.strptime(texto, '%d/%m/%Y').date()
        except ValueError:
            return 'Escribe una fecha válida: DD/MM/AAAA (por ejemplo 25/12/2026).', opciones_fecha()
        if fecha < hoy():
            return 'La fecha límite debe ser hoy o después.', opciones_fecha()
    return guardar_fecha(chat, fecha.isoformat())


def editar_fecha(chat, tid):
    with estado() as datos:
        c = _chat(datos, chat)
        if not any(x['id'] == tid and not x['hecha'] for x in c['tareas']):
            return 'Esa tarea ya no está pendiente.', None
        c['paso'] = {'tipo': 'fecha', 'id': tid, 'creado': hoy().isoformat()}
    return '📅 Elige la nueva fecha límite.', opciones_fecha()


def guardar_fecha(chat, fecha):
    with estado() as datos:
        c = _chat(datos, chat)
        paso = c['paso']
        if not paso or paso['tipo'] != 'fecha':
            return 'Ese formulario ya terminó. Abre /pendientes.', None
        if paso.get('id'):
            for x in c['tareas']:
                if x['id'] == paso['id']:
                    x.update(fecha=fecha, sincronizada=False)
        else:
            for titulo in paso['titulos']:
                c['tareas'].append({'id': uuid.uuid4().hex, 'titulo': titulo, 'fecha': fecha,
                                    'hecha': False, 'sincronizada': False, 'evento': False})
        c['paso'] = None
    ok, aviso = sincronizar(chat)
    mensaje = '✅ Guardado. Puedes seguir acumulando tareas en Pendientes.'
    if fecha and not ok:
        mensaje += '\n' + aviso
    return mensaje, [[('📋 Pendientes', 'm:pendientes'), ('➕ Agregar más', 'pd:nueva')]]


def completar(chat, tid):
    with estado() as datos:
        c = _chat(datos, chat)
        for x in c['tareas']:
            if x['id'] == tid:
                x.update(hecha=True, sincronizada=False)
                break
        else:
            return 'Esa tarea no existe.'
    sincronizar(chat)
    return '✅ Tarea hecha.'


def credenciales(chat):
    try:
        c = json.loads(GOOGLE.read_text())
    except (OSError, ValueError):
        return None
    if str(c.get('chat')) != str(chat):
        return None
    return c if all(c.get(k) for k in ('client_id', 'client_secret', 'refresh_token')) else None


def conexion(chat):
    if credenciales(chat):
        return '📅 Google Calendar autorizado. Pulsa Sincronizar para comprobar la conexión y enviar tareas con fecha.'
    return ('📅 Falta autorizar tu cuenta de Google una vez. La lista de tareas ya funciona aquí. '
            'Para activar Calendar hay que ejecutar setup_google_calendar.py en tu Mac con las credenciales '
            'de Google. No envíes contraseñas ni tokens por Telegram.')


def _evento(x):
    inicio = date.fromisoformat(x['fecha'])
    return {'summary': ('✅ ' if x['hecha'] else '📋 ') + x['titulo'],
            'description': 'Fecha límite de una tarea de Pendientes en Telegram. Gestiona la tarea desde el bot.',
            'start': {'date': inicio.isoformat()},
            'end': {'date': (inicio + timedelta(days=1)).isoformat()},
            'transparency': 'transparent', 'status': 'confirmed'}


def sincronizar(chat):
    c = credenciales(chat)
    if not c:
        return False, 'Google Calendar aún no está conectado; las tareas quedan guardadas en Telegram.'
    try:
        token = requests.post('https://oauth2.googleapis.com/token', data={
            'client_id': c['client_id'], 'client_secret': c['client_secret'],
            'refresh_token': c['refresh_token'], 'grant_type': 'refresh_token'}, timeout=15)
        token.raise_for_status()
        cab = {'Authorization': 'Bearer ' + token.json()['access_token']}
        url = 'https://www.googleapis.com/calendar/v3/calendars/%s/events' % quote(c.get('calendar_id', 'primary'), safe='')
        with estado() as datos:
            for x in _chat(datos, chat)['tareas']:
                if x['sincronizada'] or (not x['fecha'] and not x['evento']):
                    continue
                eid = 'pd' + x['id']  # base32hex, estable: reintentar no duplica eventos
                if not x['fecha']:
                    r = requests.delete(url + '/' + eid, headers=cab, timeout=15)
                    if r.status_code not in (204, 404, 410):
                        r.raise_for_status()
                    x.update(evento=False, sincronizada=True)
                    continue
                evento = _evento(x)
                r = requests.post(url, headers=cab, json=dict(evento, id=eid), timeout=15)
                if r.status_code == 409:
                    r = requests.patch(url + '/' + eid, headers=cab, json=evento, timeout=15)
                r.raise_for_status()
                x.update(evento=True, sincronizada=True)
        return True, '✅ Tareas sincronizadas con Google Calendar.'
    except (requests.RequestException, ValueError, KeyError):
        return False, '⚠️ No se pudo sincronizar con Google. Tus tareas siguen guardadas; pulsa Sincronizar para reintentar o revisa la autorización.'


def pantalla(chat, pagina=0):
    tareas = lista(chat)
    pagina = max(0, min(pagina, max(0, (len(tareas) - 1) // 8)))
    lineas = ['📋 <b>Pendientes</b> · %d tareas' % len(tareas)]
    botones = [[('➕ Agregar tareas', 'pd:nueva')]]
    for x in tareas[pagina * 8:pagina * 8 + 8]:
        fecha = date.fromisoformat(x['fecha']).strftime('%d/%m/%Y') if x['fecha'] else 'Sin fecha'
        atraso = ' · vencida' if x['fecha'] and x['fecha'] < hoy().isoformat() else ''
        nube = ' · por sincronizar' if x['fecha'] and not x['sincronizada'] else ''
        lineas.append('• %s — %s%s%s' % (escape(x['titulo']), fecha, atraso, nube))
        botones.append([('✅ ' + x['titulo'][:28], 'pd:hecha:' + x['id']),
                        ('📅 Fecha', 'pd:editar:' + x['id'])])
    if not tareas:
        lineas.append('Agrega tareas y elige su fecha límite, o déjalas sin fecha.')
    if len(tareas) > 8:
        botones.append([('⬅️', 'pd:pagina:%d' % max(0, pagina - 1)),
                        ('➡️', 'pd:pagina:%d' % (pagina + 1))])
    botones.append([('📅 Conectar Google Calendar', 'pd:google'), ('🔄 Sincronizar', 'pd:sync')])
    return '\n'.join(lineas), botones


def boton(chat, accion, valor=''):
    if accion == 'nueva':
        return empezar(chat)
    if accion == 'cancelar':
        cancelar(chat)
        return pantalla(chat)
    if accion == 'fecha':
        if valor == 'otra':
            return 'Escribe la fecha límite: DD/MM/AAAA.', [[('✖️ Cancelar', 'pd:cancelar')]]
        dias = {'hoy': 0, 'manana': 1, 'semana': 7}
        if valor not in dias and valor != 'ninguna':
            return pantalla(chat)
        return guardar_fecha(chat, None if valor == 'ninguna' else (hoy() + timedelta(days=dias[valor])).isoformat())
    if accion == 'editar':
        return editar_fecha(chat, valor)
    if accion == 'hecha':
        completar(chat, valor)
        return pantalla(chat)
    if accion == 'google':
        botones = [[('🔄 Sincronizar', 'pd:sync'), ('Volver', 'm:pendientes')]]
        if credenciales(chat):
            botones.insert(0, [('Abrir Google Calendar', 'https://calendar.google.com/')])
        return conexion(chat), botones
    if accion == 'sync':
        return sincronizar(chat)[1], [[('📋 Pendientes', 'm:pendientes')]]
    if accion == 'pagina':
        try:
            return pantalla(chat, int(valor))
        except ValueError:
            pass
    return pantalla(chat)
