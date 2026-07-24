import pandas as pd
from pathlib import Path
import unicodedata

def quitar_acentos(texto):
    if not isinstance(texto, str):
        return texto
    normalizado = unicodedata.normalize('NFKD', texto)
    return normalizado.encode('ASCII', 'ignore').decode('utf-8').upper()


def procesar_supercias():
    """Procesa el directorio de companias de SUPERCIAS y genera supercias.csv."""

    ruta_excel = Path("datos_macroentorno/bronze/SUPERCIAS/excels/Companias.xlsx")
    ruta_salida = Path("datos_macroentorno/silver_pruebas")
    ruta_salida.mkdir(parents=True, exist_ok=True)

    print("Leyendo Excel de SUPERCIAS (217k+ filas, puede tardar)...")
    df = pd.read_excel(ruta_excel, header=4, dtype=str)
    print(f"   Filas leidas: {len(df)}")

    # Normalizar nombres de columnas
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace(".", "", regex=False)
    )

    # Mapa de renombrado (acentos -> sin acentos)
    rename_map = {
        "no_fila": "no_fila",
        "situaci\u00f3n_legal": "situacion_legal",
        "pa\u00eds": "pais",
        "regi\u00f3n": "region",
        "cant\u00f3n": "canton",
        "n\u00famero": "numero",
        "intersecci\u00f3n": "interseccion",
        "tel\u00e9fono": "telefono",
        "\u00faltimo_balance": "ultimo_balance",
        "present\u00f3_balance_inicial": "presento_balance_inicial",
        "fecha_presentaci\u00f3n_balance_inicial": "fecha_presentacion_balance_inicial",
    }
    df = df.rename(columns=rename_map)

    # Filtrar solo companias de Ecuador
    if "pais" in df.columns:
        df = df[df["pais"].str.upper() == "ECUADOR"].copy()
        print(f"   Filas Ecuador: {len(df)}")

    # Convertir capital suscrito a numerico (formato: 48.200,00)
    if "capital_suscrito" in df.columns:
        df["capital_suscrito"] = (
            df["capital_suscrito"]
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df["capital_suscrito"] = pd.to_numeric(df["capital_suscrito"], errors="coerce")
    df['provincia'] = df['provincia'].apply(quitar_acentos)

    # Agregar por provincia, canton, sector CIIU y situacion legal
    grupo_cols = ["provincia", "canton", "ciiu_nivel_1", "situacion_legal"]
    grupo_cols = [c for c in grupo_cols if c in df.columns]

    resumen = (
        df.groupby(grupo_cols)
        .agg(
            num_companias=("ruc", "count"),
            capital_total=("capital_suscrito", "sum"),
            capital_promedio=("capital_suscrito", "mean"),
        )
        .reset_index()
    )

    resumen["capital_total"] = resumen["capital_total"].round(2)
    resumen["capital_promedio"] = resumen["capital_promedio"].round(2)

    archivo_salida = ruta_salida / "supercias.csv"
    resumen.to_csv(archivo_salida, index=False)

    nulos = resumen.isnull().sum().sum()
    print(f"\n=== supercias.csv generado ===")
    print(f"   Filas:  {len(resumen)}")
    print(f"   Nulos:  {nulos}")
    print(f"   Guardado en: {archivo_salida}")


if __name__ == "__main__":
    procesar_supercias()
