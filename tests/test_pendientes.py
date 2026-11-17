import importlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import requests
import pendientes as P


class Pendientes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rutas = (P.ESTADO, P.GOOGLE)
        P.ESTADO = Path(self.tmp.name) / 'pendientes.json'
        P.GOOGLE = Path(self.tmp.name) / 'google_calendar.json'
        self.fecha = patch.object(P, 'hoy', return_value=date(2026, 11, 16))
        self.fecha.start()

    def tearDown(self):
        self.fecha.stop()
        P.ESTADO, P.GOOGLE = self.rutas
        self.tmp.cleanup()

    def crear(self, titulo='Enviar documento', fecha='hoy'):
        P.empezar(7)
        P.con_texto(7, titulo)
        P.boton(7, 'fecha', fecha)
        return P.lista(7)[0]

    def conectar(self):
        P.GOOGLE.write_text(json.dumps({'chat': '7', 'client_id': 'falso',
                                       'client_secret': 'falso', 'refresh_token': 'falso'}))

    def test_acumula_varias_y_sin_fecha(self):
        self.crear('Enviar documento\nComprar cuaderno', 'ninguna')
        self.assertEqual(len(P.lista(7)), 2)
        self.assertTrue(all(x['fecha'] is None for x in P.lista(7)))
        self.assertEqual(P.lista(8), [])

    def test_formulario_persiste_al_recargar_modulo(self):
        P.empezar(7)
        P.con_texto(7, 'Terminar informe')
        rutas = P.ESTADO, P.GOOGLE
        importlib.reload(P)
        P.ESTADO, P.GOOGLE = rutas
        with patch.object(P, 'hoy', return_value=date(2026, 11, 16)):
            P.boton(7, 'fecha', 'manana')
        self.assertEqual(P.lista(7)[0]['fecha'], '2026-11-17')

    def test_fecha_invalida_no_pierde_titulo(self):
        P.empezar(7)
        P.con_texto(7, 'Informe')
        self.assertIn('válida', P.con_texto(7, '31/02/2027')[0])
        self.assertIn('hoy o después', P.con_texto(7, '15/11/2026')[0])
        P.con_texto(7, '20/11/2026')
        self.assertEqual(P.lista(7)[0]['fecha'], '2026-11-20')

    def test_completar_y_cambiar_fecha_no_tocan_otro_chat(self):
        x = self.crear()
        P.completar(8, x['id'])
        self.assertEqual(len(P.lista(7)), 1)
        P.editar_fecha(7, x['id'])
        P.boton(7, 'fecha', 'semana')
        self.assertEqual(P.lista(7)[0]['fecha'], '2026-11-23')
        P.completar(7, x['id'])
        self.assertEqual(P.lista(7), [])
        self.assertEqual(len(P.lista(7, hechas=True)), 1)

    def test_pantalla_escapa_html_y_pagina(self):
        self.crear('\n'.join(['<Tarea %d>' % i for i in range(12)]))
        texto, _ = P.pantalla(7)
        self.assertNotIn('<Tarea', texto)
        self.assertEqual(texto.count('•'), 8)
        self.assertEqual(P.pantalla(7, 1)[0].count('•'), 4)

    def test_formulario_de_ayer_no_se_come_un_gasto_hoy(self):
        P.empezar(7)
        with patch.object(P, 'hoy', return_value=date(2026, 11, 17)):
            self.assertFalse(P.esperando(7))

    def test_credenciales_no_se_comparten_con_otro_chat(self):
        self.conectar()
        with patch.object(P.requests, 'post') as post:
            self.assertFalse(P.sincronizar(8)[0])
            post.assert_not_called()

    def test_fallo_de_google_preserva_tarea(self):
        x = self.crear()
        self.conectar()
        with patch.object(P.requests, 'post', side_effect=requests.Timeout):
            self.assertFalse(P.sincronizar(7)[0])
        self.assertEqual(P.lista(7)[0]['id'], x['id'])
        self.assertFalse(P.lista(7)[0]['sincronizada'])

    def test_reintento_usa_mismo_id_y_actualiza_sin_duplicar(self):
        x = self.crear()
        self.conectar()
        token = Mock(status_code=200)
        token.json.return_value = {'access_token': 'falso'}
        conflicto = Mock(status_code=409)
        with patch.object(P.requests, 'post', side_effect=[token, conflicto]) as post, \
                patch.object(P.requests, 'patch', return_value=Mock(status_code=200)) as editar:
            self.assertTrue(P.sincronizar(7)[0])
        self.assertEqual(post.call_args.kwargs['json']['id'], 'pd' + x['id'])
        self.assertTrue(editar.call_args.args[0].endswith('pd' + x['id']))
        evento = editar.call_args.kwargs['json']
        self.assertEqual(evento['start']['date'], '2026-11-16')
        self.assertEqual(evento['end']['date'], '2026-11-17')
        self.assertTrue(P.lista(7)[0]['sincronizada'])

    def test_quitar_fecha_elimina_solo_evento_propio(self):
        x = self.crear()
        with P.estado() as datos:
            datos['7']['tareas'][0]['evento'] = True
        P.editar_fecha(7, x['id'])
        P.boton(7, 'fecha', 'ninguna')
        self.conectar()
        token = Mock()
        token.json.return_value = {'access_token': 'falso'}
        with patch.object(P.requests, 'post', return_value=token), \
                patch.object(P.requests, 'delete', return_value=Mock(status_code=204)) as borrar:
            self.assertTrue(P.sincronizar(7)[0])
        self.assertTrue(borrar.call_args.args[0].endswith('pd' + x['id']))
        self.assertFalse(P.lista(7)[0]['evento'])
