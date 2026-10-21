"""El reloj de trabajo: cronometro con tope, avisos y promedios.

El modulo no guarda nada en memoria (cada llamada lee el archivo), justo para que un reinicio del
bot no se lleve el bloque que esta corriendo. Estos tests apuntan `reloj.DATA` y `reloj.ESTADO` a
un temporal y le cambian el reloj a `reloj.ahora`, asi no tocan el disco del proyecto ni esperan.
"""

import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import reloj as R  # noqa: E402


class Reloj(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        R.DATA = Path(tmp.name)
        R.ESTADO = R.DATA / "reloj.json"
        self.t = datetime(2026, 10, 21, 9, 0)
        R.ahora = lambda: self.t

    def avanzar(self, minutos):
        self.t = self.t + timedelta(minutes=minutos)

    # ---- contar

    def test_cuenta_lo_que_va(self):
        R.iniciar(1, "facebook", 45)
        self.avanzar(10)
        self.assertIn("10 min", R.estado(1))
        self.assertIn("35 min", R.estado(1))        # lo que queda del tope

    def test_no_se_pisan_dos_bloques(self):
        R.iniciar(1, "facebook", 45)
        self.assertIn("Ya tienes", R.iniciar(1, "otra cosa", 10))

    def test_dos_chats_a_la_vez_no_se_mezclan(self):
        R.iniciar(1, "facebook", 10)
        R.iniciar(2, "informe", 90)
        self.avanzar(11)
        self.assertEqual([chat for chat, _ in R.vencidos()], [1])

    # ---- avisar

    def test_avisa_al_llegar_al_tope_y_no_martillea(self):
        R.iniciar(1, "facebook", 45)
        self.avanzar(44)
        self.assertEqual(R.vencidos(), [])          # todavia no
        self.avanzar(2)
        avisos = R.vencidos()
        self.assertEqual(len(avisos), 1)
        self.assertIn("tope", avisos[0][1])
        self.assertEqual(R.vencidos(), [])          # el mismo aviso no se repite

    def test_un_segundo_aviso_y_despues_se_calla(self):
        R.iniciar(1, "facebook", 40)
        self.avanzar(41)
        R.vencidos()
        self.avanzar(20)                            # 61 min: 50% pasado el tope
        self.assertEqual(len(R.vencidos()), 1)
        self.avanzar(300)
        self.assertEqual(R.vencidos(), [])          # ya no molesta mas

    def test_sin_tope_no_avisa_nunca(self):
        R.iniciar(1, "leer")
        self.avanzar(600)
        self.assertEqual(R.vencidos(), [])

    # ---- medir

    def test_guarda_el_bloque_y_saca_el_promedio(self):
        for minutos in (30, 50):
            R.iniciar(1, "facebook", 45)
            self.avanzar(minutos)
            R.terminar(1)
        h = R.historial("facebook")
        self.assertEqual(h["veces"], 2)
        self.assertAlmostEqual(h["promedio"], 40.0, places=1)
        self.assertEqual(h["minimo"], 30)
        self.assertEqual(h["maximo"], 50)
        self.assertIn("40 min", R.tareas())

    def test_dice_si_te_pasaste_del_tope(self):
        R.iniciar(1, "facebook", 30)
        self.avanzar(45)
        self.assertIn("pasaste", R.terminar(1))

    def test_la_misma_tarea_aunque_se_escriba_distinto(self):
        for nombre in ("Facebook", "  facebook  ", "FACEBOOK"):
            R.iniciar(1, nombre, 45)
            self.avanzar(30)
            R.terminar(1)
        self.assertEqual(R.historial("facebook")["veces"], 3)

    def test_cortar_no_guarda_nada(self):
        R.iniciar(1, "facebook", 45)
        self.avanzar(30)
        self.assertIn("no se guardó", R.cortar(1))
        self.assertEqual(R.historial("facebook")["veces"], 0)

    def test_terminar_sin_nada_corriendo_no_explota(self):
        self.assertIn("No tenías", R.terminar(1))
        self.assertIn("No tenías", R.cortar(1))

    # ---- el reinicio del bot

    def test_un_reinicio_no_se_lleva_el_bloque(self):
        """`finanzas-autoupdate` reinicia el bot cada vez que hay algo nuevo en main."""
        R.iniciar(1, "facebook", 45)
        self.avanzar(50)
        self.assertEqual(len(R.vencidos()), 1)      # se lee del archivo, no de memoria
        self.assertIn("facebook", R.estado(1))

    def test_un_archivo_roto_no_tumba_el_bot(self):
        R.ESTADO.write_text("{esto no es json")
        self.assertIn("nada corriendo", R.estado(1))
        self.assertEqual(R.vencidos(), [])
        self.assertIn("▶️", R.iniciar(1, "facebook", 45))
