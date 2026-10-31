import os

# Los tests nunca salen a internet a buscar el tipo de cambio.
os.environ["TC_AUTO"] = "0"

# Los tests corren siempre sobre el MISMO perfil de referencia, sin importar en qué instalación
# estén corriendo. El `.env` de cada servidor dice quién es su dueño, y los tests comprueban el
# CÓDIGO, no los datos de esa persona: la mayoría afirma cosas como "el resumen dice S/ 45.00"
# o "la categoría es Restaurantes y cafés", que en otro perfil son falsas sin que nada esté mal.
#
# Sin esto, en la instalación en ruso fallaban 114 de 249 — y `deploy/auto-actualizar.sh`
# **deshace la actualización cuando los tests fallan**, así que ese sistema no podía
# actualizarse solo nunca. Se descubrió el 31/10/2026.
#
# Lo que sí tiene que valer para todos (que un perfil no nombre categorías inexistentes, que
# cada idioma traduzca todo) vive en tests/test_perfiles.py y tests/test_idiomas.py, que
# recorren *todos* los perfiles e idiomas por su cuenta.
for clave, valor in (("PERFIL", "jose"), ("IDIOMA", "es"), ("MONEDA_BASE", "PEN"),
                     ("ZONA_HORARIA", "America/Lima")):
    os.environ[clave] = valor
