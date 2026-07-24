
import pandas as pd
from pathlib import Path
import unicodedata

def quitar_acentos(texto):
    if not isinstance(texto, str):
        return texto
    normalizado = unicodedata.normalize('NFKD', texto)
    return normalizado.encode('ASCII', 'ignore').decode('utf-8').upper()


def procesar_mineduc():
    """Lee mineduc_historico.xlsx y genera mineduc.csv agregado por canton y anio."""

    ruta_entrada = Path("datos_macroentorno/bronze/MINEDUC/excels/mineduc_historico.xlsx")
    ruta_salida  = Path("datos_macroentorno/silver_pruebas")
    ruta_salida.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(ruta_entrada)

    # Agregar por provincia, canton y anio (suma de todos los sostenimientos)
    df_agg = (
        df.groupby(["provincia", "canton", "anio"], as_index=False)
          .agg(
              total_estudiantes=("total_estudiantes", "sum"),
              bachilleres_3ero=("bachilleres_3ero", "sum"),
          )
    )

    # Normalizar texto
    df_agg["provincia"] = df_agg["provincia"].str.strip().str.upper()
    df_agg["canton"]    = df_agg["canton"].str.strip().str.upper()
    df['provincia'] = df['provincia'].apply(quitar_acentos)
    df['canton'] = df['canton'].apply(quitar_acentos)

    # Ordenar
    df_agg = df_agg.sort_values(["anio", "provincia", "canton"]).reset_index(drop=True)

    # Guardar
    archivo = ruta_salida / "mineduc.csv"
    df_agg.to_csv(archivo, index=False)

    nulos = df_agg.isnull().sum().sum()
    print(f"  -> mineduc.csv  : {len(df_agg)} filas | {nulos} nulos")

    return df_agg


if __name__ == "__main__":
    print("=== Procesando MINEDUC ===")
    procesar_mineduc()
    print("=== Listo ===")
