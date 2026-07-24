"""
Bloque 1 (Banco Central del Ecuador): normalizacion de 5 archivos crudos
"""
import os
import pandas as pd
from codigo_fuente.transform.common import (
    convertir_numero, convertir_fecha, extraer_anio, normalizar_texto,
    eliminar_duplicados_log, resumen_nulos,
)

# === DESTINO DE PRUEBAS (no toca silver de produccion) ===
DEST = "datos_macroentorno/silver_pruebas"


def procesar_expectativas(path: str = "datos_macroentorno/bronze/BCE/excels/IEE.xlsx") -> pd.DataFrame:
    """Indice de Expectativas Empresariales mensual (historico desde 2010)."""
    tabla = pd.read_excel(path, sheet_name="IEE", header=7)
    tabla = tabla.rename(columns={
        "Fecha": "fecha",
        "IEE Global (2)": "iee_global",
        "Comercio": "comercio",
        "Construcción": "construccion",
        "Manufactura": "manufactura",
        "Servicios": "servicios",
    })
    tabla["fecha"] = convertir_fecha(tabla["fecha"], formato_dia_primero=True)
    columnas_numericas = ["iee_global", "comercio", "construccion", "manufactura", "servicios"]
    for campo in columnas_numericas:
        tabla[campo] = convertir_numero(tabla[campo])
    tabla = tabla.dropna(subset=["fecha"])
    tabla = eliminar_duplicados_log(tabla, claves=["fecha"], etiqueta="IEE")
    resumen_nulos(tabla, "IEE")
    return tabla.sort_values("fecha").reset_index(drop=True)


def _normalizar_serie_temporal(path: str, campo_valor: str) -> pd.DataFrame:
    """Rutina comun a Petroleo.xlsx y Riesgo_del_pais.xlsx."""
    tabla = pd.read_excel(path, sheet_name="Ark1", header=1)
    tabla.columns = ["fecha", campo_valor]
    tabla["fecha"] = convertir_fecha(tabla["fecha"], formato_dia_primero=True)
    tabla[campo_valor] = convertir_numero(tabla[campo_valor])
    tabla = tabla.dropna(subset=["fecha"])
    tabla = eliminar_duplicados_log(tabla, claves=["fecha"], etiqueta=campo_valor)
    resumen_nulos(tabla, campo_valor)
    return tabla.sort_values("fecha").reset_index(drop=True)


def procesar_riesgo_pais(path: str = "datos_macroentorno/bronze/BCE/excels/Riesgos_del_pais.xlsx") -> pd.DataFrame:
    """Riesgo pais diario, expresado en puntos basicos (EMBI)."""
    return _normalizar_serie_temporal(path, "riesgo_pais_pb")


def procesar_wti(path: str = "datos_macroentorno/bronze/BCE/excels/Petroleo.xlsx") -> pd.DataFrame:
    """Cotizacion diaria del petroleo WTI (USD por barril)."""
    return _normalizar_serie_temporal(path, "precio_petroleo_wti")


def procesar_indicadores_mercado() -> pd.DataFrame:
    """Une WTI y riesgo pais en una sola tabla diaria."""
    wti = procesar_wti()
    riesgo = procesar_riesgo_pais()
    combinado = pd.merge(wti, riesgo, on="fecha", how="outer")
    return combinado.sort_values("fecha").reset_index(drop=True)


def procesar_vab(path: str = "datos_macroentorno/bronze/BCE/excels/VAB 2018-2023.xlsx") -> pd.DataFrame:
    """Valor Agregado Bruto (miles USD) desagregado por provincia/canton/sector."""
    tabla = pd.read_excel(path, sheet_name="DATA")
    tabla = tabla.rename(columns={
        "AÑO": "anio",
        "CÓDIGO PROVINCIA": "cod_provincia",
        "PROVINCIA": "provincia",
        "CÓDIGO CANTÓN": "cod_canton",
        "CANTÓN": "CANTÓN",
        "SECTOR": "sector",
        "VALOR": "vab_miles_usd",
    })
    tabla["anio"] = convertir_numero(tabla["anio"]).astype("Int64")
    tabla["cod_provincia"] = convertir_numero(tabla["cod_provincia"]).astype("Int64")
    tabla["cod_canton"] = convertir_numero(tabla["cod_canton"]).astype("Int64")
    tabla["vab_miles_usd"] = convertir_numero(tabla["vab_miles_usd"])
    tabla["provincia"] = normalizar_texto(tabla["provincia"])
    tabla["CANTÓN"] = normalizar_texto(tabla["CANTÓN"])
    tabla["sector"] = normalizar_texto(tabla["sector"])
    tabla = tabla.dropna(subset=["provincia", "anio", "vab_miles_usd"])
    tabla = eliminar_duplicados_log(
        tabla, claves=["anio", "cod_canton", "sector"], etiqueta="VAB"
    )
    resumen_nulos(tabla, "VAB")
    return tabla.reset_index(drop=True)


def procesar_pib(path: str = "datos_macroentorno/bronze/BCE/excels/PIB.xlsx") -> pd.DataFrame:
    """PIB real anual (millones USD), PIB per capita nominal y variacion %."""
    tabla = pd.read_excel(path, sheet_name="Hoja1")
    tabla = tabla.rename(columns={
        "AÑO": "anio_raw",
        "PIB 2018 = 100.1": "pib_real_musd",
        "VAR ANUAL PIB": "variacion_pib_pct",
        "PIB PER CÁPITA NOMINAL": "pib_percapita_nominal",
    })
    filas_con_anio = tabla["anio_raw"].astype(str).str.match(r"^\d{4}")
    tabla = tabla[filas_con_anio]
    tabla["anio"] = extraer_anio(tabla["anio_raw"])
    tabla = tabla.dropna(subset=["anio"])
    campos_numericos = ["pib_real_musd", "pib_percapita_nominal", "variacion_pib_pct"]
    for campo in campos_numericos:
        tabla[campo] = convertir_numero(tabla[campo])
    tabla["variacion_pib_pct"] = (tabla["variacion_pib_pct"] * 100).round(3)
    tabla = tabla[["anio", "pib_real_musd", "pib_percapita_nominal", "variacion_pib_pct"]]
    tabla = eliminar_duplicados_log(tabla, claves=["anio"], etiqueta="PIB")
    resumen_nulos(tabla, "PIB")
    return tabla.reset_index(drop=True)


def exportar_silver():
    """Genera todos los archivos de la capa Silver en DEST (pruebas)."""
    os.makedirs(DEST, exist_ok=True)
    print(f"Destino: {os.path.abspath(DEST)}\n")

    print("Generando pib.csv...")
    procesar_pib().to_csv(f"{DEST}/pib.csv", index=False)

    print("Generando vab.csv...")
    procesar_vab().to_csv(f"{DEST}/vab.csv", index=False)

    print("Generando iee.csv...")
    procesar_expectativas().to_csv(f"{DEST}/iee.csv", index=False)

    print("Generando indicadores_mercado.csv...")
    procesar_indicadores_mercado().to_csv(f"{DEST}/indicadores_mercado.csv", index=False)

    print("\nArchivos Silver generados correctamente en:", DEST)


if __name__ == "__main__":
    exportar_silver()

