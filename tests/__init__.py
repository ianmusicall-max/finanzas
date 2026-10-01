import os

# Los tests nunca salen a internet a buscar el tipo de cambio.
os.environ["TC_AUTO"] = "0"
