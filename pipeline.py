"""
pipeline.py — Punto de entrada oficial del pipeline ETL del proyecto.
Ejecuta el proceso RPA completo (Bronze -> Silver -> SQLite -> Reportes).
"""
import subprocess
import sys
import os

RUTA_RPA = os.path.join(os.path.dirname(__file__), "datos_macroentorno", "rpa", "rpa_macroentorno.py")

if __name__ == "__main__":
    resultado = subprocess.run([sys.executable, RUTA_RPA], cwd=os.path.dirname(RUTA_RPA))
    sys.exit(resultado.returncode)