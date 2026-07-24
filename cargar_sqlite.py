import pandas as pd
import sqlite3
import os

SILVER = "datos_macroentorno/silver"
DB     = "datos_macroentorno/macroentorno.db"

conn = sqlite3.connect(DB)

archivos_cargados = 0
for archivo in os.listdir(SILVER):
    if archivo.endswith(".csv"):
        tabla = archivo.replace(".csv", "")
        df = pd.read_csv(os.path.join(SILVER, archivo))
        df.to_sql(tabla, conn, if_exists="replace", index=False)
        print(f"✔ Tabla '{tabla}' cargada: {len(df)} filas, {len(df.columns)} columnas")
        archivos_cargados += 1

print(f"\n {archivos_cargados} tablas cargadas en {DB}")

# Mostrar tablas creadas
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("\nTablas en la base de datos:")
for row in cur.fetchall():
    print(f"  - {row[0]}")

conn.close()
