# =============================================================================
# RPA MACROENTORNO ECONÓMICO - PROCESO AUTOMATIZADO
# Creado por: RPA Automatizado
# Descripción: Extrae, transforma y carga datos del macroentorno económico
# Ubicación de este script: datos_macroentorno/rpa/rpa_macroentorno.py
#   (por eso todas las rutas usan "../" para subir al nivel de datos_macroentorno)
# =============================================================================

import os
import sys
import json
import sqlite3
import unicodedata
from datetime import datetime

# === UTILIDADES ===

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_LINES = []

def rpa_log(mensaje, nivel="INFO"):
    """Registra un mensaje en el log del RPA."""
    linea = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{nivel}] {mensaje}"
    LOG_LINES.append(linea)
    print(linea)

def rpa_paso(numero, total, descripcion):
    """Muestra el progreso del RPA."""
    rpa_log(f"=== PASO {numero}/{total}: {descripcion} ===")

def normalizar_texto(texto):
    """Elimina acentos y convierte a mayúsculas."""
    if not isinstance(texto, str):
        return texto
    normalizado = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return normalizado.upper().strip()

def normalizar_columnas(df):
    """Normaliza nombres de columnas: sin acentos, minúsculas, sin espacios."""
    nuevas = []
    for col in df.columns:
        nuevo = unicodedata.normalize('NFKD', str(col)).encode('ASCII', 'ignore').decode('utf-8')
        nuevo = nuevo.lower().strip().replace(' ', '_').replace('.', '').replace('(', '').replace(')', '')
        nuevo = ''.join(c if c.isalnum() or c == '_' else '_' for c in nuevo)
        while '__' in nuevo:
            nuevo = nuevo.replace('__', '_')
        nuevo = nuevo.strip('_')
        nuevas.append(nuevo)
    df.columns = nuevas
    return df

def detectar_fila_encabezado(df, max_filas=15):
    """Detecta automáticamente la fila que contiene los encabezados reales."""
    for i in range(min(max_filas, len(df))):
        fila = df.iloc[i]
        no_nulos = fila.dropna()
        if len(no_nulos) >= 2:
            textos = sum(1 for v in no_nulos if isinstance(v, str) and len(v.strip()) > 1)
            if textos >= 2:
                return i
    return 0

def corregir_provincia(nombre):
    """Corrige variantes de nombres de provincias."""
    if not isinstance(nombre, str):
        return nombre
    nombre = normalizar_texto(nombre)
    correcciones = {
        "SANTO DOMINGO DE LOS TSACHILAS": "SANTO DOMINGO",
        "SANTO DOMINGO DE LOS TSCHILAS": "SANTO DOMINGO",
    }
    return correcciones.get(nombre, nombre)


# === CONFIGURACIÓN ===

def construir_config():
    """Define rutas y archivos reales del RPA (corregido: nombres reales de archivo
    y rutas relativas '../' porque el script corre desde la carpeta rpa/)."""
    return {
        "rutas": {
            "bronze_bce": "../bronze/BCE/excels",
            "bronze_mineduc": "../bronze/MINEDUC/excels",
            "bronze_supercias": "../bronze/SUPERCIAS/excels",
            "silver": "../rpa_silver",
            "db": "../rpa_db",
            "reportes": "../rpa_reportes",
            "logs": "../rpa_logs",
        },
        "base_datos": "rpa_macroentorno.db",
        # Archivos BCE reales (corregido: VAB tiene otro nombre; Inflacion/Empleo/Pobreza
        # no existen y se quitan; se agregan PIB, IEE, Petroleo y Riesgos_del_pais que sí existen)
        "archivos_bce": [
            {"archivo": "VAB 2018-2023.xlsx", "tabla": "rpa_vab"},
            {"archivo": "PIB.xlsx", "tabla": "rpa_pib"},
            {"archivo": "IEE.xlsx", "tabla": "rpa_iee"},
            {"archivo": "Petroleo.xlsx", "tabla": "rpa_petroleo"},
            {"archivo": "Riesgos_del_pais.xlsx", "tabla": "rpa_riesgo_pais"},
        ],
        # MINEDUC: corregido nombre real de archivo
        "archivos_mineduc": [
            {"archivo": "mineduc_historico.xlsx", "tabla": "rpa_mineduc"},
        ],
        # SUPERCIAS: el nombre ya coincidía con el archivo real
        "archivos_supercias": [
            {"archivo": "Companias.xlsx", "tabla": "rpa_supercias"},
        ],
    }


# === ETAPA 1: CREAR DIRECTORIOS ===

def rpa_etapa1_crear_directorios(config):
    """Crea los directorios necesarios para el RPA."""
    rpa_paso(1, 6, "CREACIÓN DE DIRECTORIOS RPA")

    directorios = [
        config["rutas"]["silver"],
        config["rutas"]["db"],
        config["rutas"]["reportes"],
        config["rutas"]["logs"],
    ]

    for d in directorios:
        os.makedirs(d, exist_ok=True)
        rpa_log(f"  [RPA creó directorio] {d}")

    return True


# === ETAPA 2: PROCESAR BCE ===

def rpa_etapa2_procesar_bce(config):
    """Procesa todos los archivos Excel del BCE."""
    import pandas as pd
    rpa_paso(2, 6, "PROCESAMIENTO DE DATOS BCE")

    ruta_bce = config["rutas"]["bronze_bce"]
    ruta_silver = config["rutas"]["silver"]
    archivos = config["archivos_bce"]
    procesados = 0

    for item in archivos:
        archivo = item["archivo"]
        tabla = item["tabla"]
        ruta_completa = os.path.join(ruta_bce, archivo)

        if not os.path.exists(ruta_completa):
            rpa_log(f"  [ADVERTENCIA] No encontrado: {ruta_completa}", "WARN")
            continue

        rpa_log(f"  Procesando: {archivo} -> {tabla}")

        try:
            # Leer Excel sin encabezado para detectar la fila correcta
            df_raw = pd.read_excel(ruta_completa, header=None, sheet_name=0)
            fila_header = detectar_fila_encabezado(df_raw)

            if fila_header > 0:
                rpa_log(f"    Encabezado detectado en fila {fila_header}")

            # Re-leer con el encabezado correcto
            df = pd.read_excel(ruta_completa, header=fila_header, sheet_name=0)

            # Eliminar filas completamente vacías
            df = df.dropna(how='all')

            # Normalizar columnas
            df = normalizar_columnas(df)

            # Si tiene columna de provincia, normalizar nombres
            col_provincia = None
            for posible in ['provincia', 'provincias', 'province']:
                if posible in df.columns:
                    col_provincia = posible
                    break

            if col_provincia:
                df[col_provincia] = df[col_provincia].apply(lambda x: corregir_provincia(x) if isinstance(x, str) else x)
                rpa_log(f"    Provincias normalizadas en columna '{col_provincia}'")

            # Guardar CSV
            csv_path = os.path.join(ruta_silver, f"{tabla}.csv")
            df.to_csv(csv_path, index=False, encoding='utf-8')
            rpa_log(f"    [RPA creó archivo] {csv_path} ({len(df)} filas, {len(df.columns)} columnas)")
            procesados += 1

        except Exception as e:
            rpa_log(f"    [ERROR] al procesar {archivo}: {str(e)}", "ERROR")

    rpa_log(f"  BCE completado: {procesados}/{len(archivos)} archivos procesados")
    return procesados


# === ETAPA 3: PROCESAR MINEDUC ===

def rpa_etapa3_procesar_mineduc(config):
    """Procesa los archivos Excel del MINEDUC."""
    import pandas as pd
    rpa_paso(3, 6, "PROCESAMIENTO DE DATOS MINEDUC")

    ruta_mineduc = config["rutas"]["bronze_mineduc"]
    ruta_silver = config["rutas"]["silver"]
    archivos = config["archivos_mineduc"]
    procesados = 0

    for item in archivos:
        archivo = item["archivo"]
        tabla = item["tabla"]
        ruta_completa = os.path.join(ruta_mineduc, archivo)

        if not os.path.exists(ruta_completa):
            rpa_log(f"  [ADVERTENCIA] No encontrado: {ruta_completa}", "WARN")
            continue

        rpa_log(f"  Procesando: {archivo} -> {tabla}")

        try:
            df_raw = pd.read_excel(ruta_completa, header=None, sheet_name=0)
            fila_header = detectar_fila_encabezado(df_raw)

            if fila_header > 0:
                rpa_log(f"    Encabezado detectado en fila {fila_header}")

            df = pd.read_excel(ruta_completa, header=fila_header, sheet_name=0)
            df = df.dropna(how='all')
            df = normalizar_columnas(df)

            # Normalizar provincias
            col_provincia = None
            for posible in ['provincia', 'provincias', 'province', 'provincia_registro']:
                if posible in df.columns:
                    col_provincia = posible
                    break

            if col_provincia:
                df[col_provincia] = df[col_provincia].apply(lambda x: corregir_provincia(x) if isinstance(x, str) else x)
                rpa_log(f"    Provincias normalizadas en columna '{col_provincia}'")

            csv_path = os.path.join(ruta_silver, f"{tabla}.csv")
            df.to_csv(csv_path, index=False, encoding='utf-8')
            rpa_log(f"    [RPA creó archivo] {csv_path} ({len(df)} filas, {len(df.columns)} columnas)")
            procesados += 1

        except Exception as e:
            rpa_log(f"    [ERROR] al procesar {archivo}: {str(e)}", "ERROR")

    rpa_log(f"  MINEDUC completado: {procesados}/{len(archivos)} archivos procesados")
    return procesados


# === ETAPA 4: PROCESAR SUPERCIAS ===

def rpa_etapa4_procesar_supercias(config):
    """Procesa los archivos Excel de SUPERCIAS."""
    import pandas as pd
    rpa_paso(4, 6, "PROCESAMIENTO DE DATOS SUPERCIAS")

    ruta_supercias = config["rutas"]["bronze_supercias"]
    ruta_silver = config["rutas"]["silver"]
    archivos = config["archivos_supercias"]
    procesados = 0

    for item in archivos:
        archivo = item["archivo"]
        tabla = item["tabla"]
        ruta_completa = os.path.join(ruta_supercias, archivo)

        if not os.path.exists(ruta_completa):
            rpa_log(f"  [ADVERTENCIA] No encontrado: {ruta_completa}", "WARN")
            continue

        rpa_log(f"  Procesando: {archivo} -> {tabla}")

        try:
            df_raw = pd.read_excel(ruta_completa, header=None, sheet_name=0)
            fila_header = detectar_fila_encabezado(df_raw)

            if fila_header > 0:
                rpa_log(f"    Encabezado detectado en fila {fila_header}")

            df = pd.read_excel(ruta_completa, header=fila_header, sheet_name=0)
            df = df.dropna(how='all')
            df = normalizar_columnas(df)

            # Normalizar provincias
            col_provincia = None
            for posible in ['provincia', 'provincias', 'province', 'provincia_compania']:
                if posible in df.columns:
                    col_provincia = posible
                    break

            if col_provincia:
                df[col_provincia] = df[col_provincia].apply(
                    lambda x: corregir_provincia(x) if isinstance(x, str) else x
                )
                rpa_log(f"    Provincias normalizadas en columna '{col_provincia}'")

            csv_path = os.path.join(ruta_silver, f"{tabla}.csv")
            df.to_csv(csv_path, index=False, encoding='utf-8')
            rpa_log(f"    [RPA creó archivo] {csv_path} ({len(df)} filas, {len(df.columns)} columnas)")
            procesados += 1

        except Exception as e:
            rpa_log(f"    [ERROR] al procesar {archivo}: {str(e)}", "ERROR")

    rpa_log(f"  SUPERCIAS completado: {procesados}/{len(archivos)} archivos procesados")
    return procesados


# === ETAPA 5: CARGAR EN SQLITE ===

def rpa_etapa5_cargar_sqlite(config):
    """Carga todos los CSV del silver RPA en una base SQLite."""
    import pandas as pd
    rpa_paso(5, 6, "CARGA EN BASE DE DATOS SQLITE")

    ruta_silver = config["rutas"]["silver"]
    ruta_db = config["rutas"]["db"]
    nombre_db = config["base_datos"]
    db_path = os.path.join(ruta_db, nombre_db)

    # Buscar CSVs generados por el RPA
    archivos_csv = [f for f in os.listdir(ruta_silver) if f.endswith('.csv')]

    if not archivos_csv:
        rpa_log("  [ADVERTENCIA] No hay archivos CSV en rpa_silver/ para cargar", "WARN")
        return 0

    # Eliminar base anterior si existe
    if os.path.exists(db_path):
        os.remove(db_path)
        rpa_log(f"  Base de datos anterior eliminada: {db_path}")

    # Crear conexión
    conn = sqlite3.connect(db_path)
    tablas_cargadas = 0

    for csv_file in sorted(archivos_csv):
        nombre_tabla = csv_file.replace('.csv', '')
        csv_path = os.path.join(ruta_silver, csv_file)

        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
            df.to_sql(nombre_tabla, conn, if_exists='replace', index=False)
            rpa_log(f"  [RPA cargó tabla] {nombre_tabla}: {len(df)} filas, {len(df.columns)} columnas")
            tablas_cargadas += 1
        except Exception as e:
            rpa_log(f"  [ERROR] al cargar {csv_file}: {str(e)}", "ERROR")

    conn.close()
    rpa_log(f"  [RPA creó base de datos] {db_path} con {tablas_cargadas} tablas")
    return tablas_cargadas


# === ETAPA 6: GENERAR REPORTES ===

def _buscar_columna(cols, claves):
    """Busca la primera columna cuyo nombre contenga alguna de las claves dadas."""
    for c in cols:
        cl = c.lower()
        for k in claves:
            if k in cl:
                return c
    return None


def rpa_etapa6_generar_reportes(config):
    """Genera reportes analíticos desde la base SQLite del RPA."""
    import pandas as pd
    rpa_paso(6, 6, "GENERACIÓN DE REPORTES RPA")

    ruta_db = config["rutas"]["db"]
    ruta_reportes = config["rutas"]["reportes"]
    nombre_db = config["base_datos"]
    db_path = os.path.join(ruta_db, nombre_db)

    if not os.path.exists(db_path):
        rpa_log("  [ERROR] No se encontró la base de datos RPA", "ERROR")
        return 0

    conn = sqlite3.connect(db_path)
    reportes_generados = 0

    # --- Descubrir tablas y columnas disponibles ---
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tablas = [row[0] for row in cursor.fetchall()]
    rpa_log(f"  Tablas disponibles: {', '.join(tablas)}")

    # Diccionario de columnas por tabla
    columnas_por_tabla = {}
    for tabla in tablas:
        cursor.execute(f"PRAGMA table_info({tabla})")
        cols = [row[1] for row in cursor.fetchall()]
        columnas_por_tabla[tabla] = cols
        rpa_log(f"    {tabla}: {cols}")

    # --- REPORTE 1: Resumen general de tablas ---
    try:
        resumen = []
        for tabla in tablas:
            cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
            n_filas = cursor.fetchone()[0]
            n_cols = len(columnas_por_tabla[tabla])
            resumen.append({
                'tabla': tabla,
                'filas': n_filas,
                'columnas': n_cols,
            })
        df_resumen = pd.DataFrame(resumen)
        out = os.path.join(ruta_reportes, "rpa_1_resumen_tablas.csv")
        df_resumen.to_csv(out, index=False, encoding='utf-8')
        rpa_log(f"  [RPA creó reporte] {out}")
        reportes_generados += 1
    except Exception as e:
        rpa_log(f"  [ERROR] en reporte 1 (resumen tablas): {str(e)}", "ERROR")

    # --- REPORTE 2: VAB por provincia ---
    try:
        if 'rpa_vab' in tablas:
            cols = columnas_por_tabla['rpa_vab']
            col_prov = _buscar_columna(cols, ['provincia'])
            col_val = _buscar_columna(cols, ['vab', 'valor', 'total', 'pib'])
            if col_prov and col_val:
                sql = f"""
                    SELECT {col_prov} as provincia,
                           ROUND(SUM(CAST({col_val} AS REAL)), 2) as vab_total,
                           COUNT(*) as registros
                    FROM rpa_vab
                    WHERE {col_prov} IS NOT NULL
                    GROUP BY {col_prov}
                    ORDER BY vab_total DESC
                """
                df = pd.read_sql(sql, conn)
            else:
                df = pd.read_sql("SELECT * FROM rpa_vab LIMIT 20", conn)
            out = os.path.join(ruta_reportes, "rpa_2_vab_provincia.csv")
            df.to_csv(out, index=False, encoding='utf-8')
            rpa_log(f"  [RPA creó reporte] {out}")
            reportes_generados += 1
    except Exception as e:
        rpa_log(f"  [ERROR] en reporte 2 (VAB por provincia): {str(e)}", "ERROR")

    # --- REPORTE 3: Empresas por provincia (SUPERCIAS) ---
    try:
        if 'rpa_supercias' in tablas:
            cols = columnas_por_tabla['rpa_supercias']
            col_prov = _buscar_columna(cols, ['provincia'])
            if col_prov:
                sql = f"""
                    SELECT {col_prov} as provincia, COUNT(*) as total_empresas
                    FROM rpa_supercias
                    WHERE {col_prov} IS NOT NULL
                    GROUP BY {col_prov}
                    ORDER BY total_empresas DESC
                """
                df = pd.read_sql(sql, conn)
            else:
                df = pd.read_sql("SELECT * FROM rpa_supercias LIMIT 20", conn)
            out = os.path.join(ruta_reportes, "rpa_3_empresas_provincia.csv")
            df.to_csv(out, index=False, encoding='utf-8')
            rpa_log(f"  [RPA creó reporte] {out}")
            reportes_generados += 1
    except Exception as e:
        rpa_log(f"  [ERROR] en reporte 3 (empresas por provincia): {str(e)}", "ERROR")

    # --- REPORTE 4: Estudiantes por provincia (MINEDUC) ---
    try:
        if 'rpa_mineduc' in tablas:
            cols = columnas_por_tabla['rpa_mineduc']
            col_prov = _buscar_columna(cols, ['provincia'])
            col_est = _buscar_columna(cols, ['estudiante', 'matricula', 'total'])
            if col_prov and col_est:
                sql = f"""
                    SELECT {col_prov} as provincia,
                           SUM(CAST({col_est} AS INTEGER)) as total_estudiantes,
                           COUNT(*) as registros
                    FROM rpa_mineduc
                    WHERE {col_prov} IS NOT NULL
                    GROUP BY {col_prov}
                    ORDER BY total_estudiantes DESC
                """
                df = pd.read_sql(sql, conn)
            elif col_prov:
                sql = f"""
                    SELECT {col_prov} as provincia, COUNT(*) as registros
                    FROM rpa_mineduc
                    WHERE {col_prov} IS NOT NULL
                    GROUP BY {col_prov}
                    ORDER BY registros DESC
                """
                df = pd.read_sql(sql, conn)
            else:
                df = pd.read_sql("SELECT * FROM rpa_mineduc LIMIT 20", conn)
            out = os.path.join(ruta_reportes, "rpa_4_estudiantes_provincia.csv")
            df.to_csv(out, index=False, encoding='utf-8')
            rpa_log(f"  [RPA creó reporte] {out}")
            reportes_generados += 1
    except Exception as e:
        rpa_log(f"  [ERROR] en reporte 4 (estudiantes por provincia): {str(e)}", "ERROR")

    # --- REPORTE 5: Indicadores macroeconómicos (PIB, IEE, Petroleo, Riesgo país) ---
    try:
        tablas_macro = [t for t in ['rpa_pib', 'rpa_iee', 'rpa_petroleo', 'rpa_riesgo_pais'] if t in tablas]
        if tablas_macro:
            resumen_macro = []
            for tabla in tablas_macro:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                n = cursor.fetchone()[0]
                resumen_macro.append({'indicador': tabla.replace('rpa_', ''), 'registros': n})
            df = pd.DataFrame(resumen_macro)
            out = os.path.join(ruta_reportes, "rpa_5_indicadores_macro.csv")
            df.to_csv(out, index=False, encoding='utf-8')
            rpa_log(f"  [RPA creó reporte] {out}")
            reportes_generados += 1
    except Exception as e:
        rpa_log(f"  [ERROR] en reporte 5 (indicadores macro): {str(e)}", "ERROR")

    # --- REPORTE 6: Perfil provincial combinado (VAB + empresas + estudiantes) ---
    try:
        if 'rpa_vab' in tablas and ('rpa_supercias' in tablas or 'rpa_mineduc' in tablas):
            cols_vab = columnas_por_tabla['rpa_vab']
            prov_vab = _buscar_columna(cols_vab, ['provincia'])
            val_vab = _buscar_columna(cols_vab, ['vab', 'valor', 'total', 'pib'])

            partes = []
            if prov_vab and val_vab:
                partes.append(f"""
                    v AS (
                        SELECT {prov_vab} as provincia,
                               ROUND(SUM(CAST({val_vab} AS REAL)), 2) as vab_total
                        FROM rpa_vab
                        WHERE {prov_vab} IS NOT NULL
                        GROUP BY {prov_vab}
                    )
                """)

            prov_sup = None
            if 'rpa_supercias' in tablas:
                prov_sup = _buscar_columna(columnas_por_tabla['rpa_supercias'], ['provincia'])
                if prov_sup:
                    partes.append(f"""
                        s AS (
                            SELECT {prov_sup} as provincia, COUNT(*) as total_empresas
                            FROM rpa_supercias
                            WHERE {prov_sup} IS NOT NULL
                            GROUP BY {prov_sup}
                        )
                    """)

            prov_min = est_min = None
            if 'rpa_mineduc' in tablas:
                cols_min = columnas_por_tabla['rpa_mineduc']
                prov_min = _buscar_columna(cols_min, ['provincia'])
                est_min = _buscar_columna(cols_min, ['estudiante', 'matricula', 'total'])
                if prov_min and est_min:
                    partes.append(f"""
                        m AS (
                            SELECT {prov_min} as provincia,
                                   SUM(CAST({est_min} AS INTEGER)) as total_estudiantes
                            FROM rpa_mineduc
                            WHERE {prov_min} IS NOT NULL
                            GROUP BY {prov_min}
                        )
                    """)

            if prov_vab and val_vab and len(partes) >= 2:
                cte = "WITH " + ",".join(partes)
                select_cols = ["v.provincia", "v.vab_total"]
                joins = ""
                if prov_sup:
                    select_cols.append("COALESCE(s.total_empresas, 0) as total_empresas")
                    joins += " LEFT JOIN s ON v.provincia = s.provincia"
                if prov_min and est_min:
                    select_cols.append("COALESCE(m.total_estudiantes, 0) as total_estudiantes")
                    joins += " LEFT JOIN m ON v.provincia = m.provincia"

                sql = f"""
                    {cte}
                    SELECT {', '.join(select_cols)}
                    FROM v
                    {joins}
                    ORDER BY v.vab_total DESC
                """
                df = pd.read_sql(sql, conn)
                out = os.path.join(ruta_reportes, "rpa_6_perfil_provincial.csv")
                df.to_csv(out, index=False, encoding='utf-8')
                rpa_log(f"  [RPA creó reporte] {out}")
                reportes_generados += 1
    except Exception as e:
        rpa_log(f"  [ERROR] en reporte 6 (perfil provincial): {str(e)}", "ERROR")

    conn.close()
    rpa_log(f"  Total de reportes generados: {reportes_generados}")
    return reportes_generados


# === GUARDAR LOG EN ARCHIVO ===

def rpa_guardar_log(config):
    """Vuelca todas las líneas de LOG_LINES a un archivo .log en disco."""
    ruta_logs = config["rutas"]["logs"]
    os.makedirs(ruta_logs, exist_ok=True)
    log_path = os.path.join(ruta_logs, f"rpa_ejecucion_{TIMESTAMP}.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(LOG_LINES))
    print(f"[RPA creó log] {log_path}")


# === MAIN ===

def main():
    config = construir_config()

    rpa_log("=" * 70)
    rpa_log("RPA MACROENTORNO ECONÓMICO - INICIO DE EJECUCIÓN")
    rpa_log("=" * 70)
    inicio = datetime.now()

    n_bce = n_min = n_sup = n_tablas = n_reportes = 0

    try:
        rpa_etapa1_crear_directorios(config)
        n_bce = rpa_etapa2_procesar_bce(config)
        n_min = rpa_etapa3_procesar_mineduc(config)
        n_sup = rpa_etapa4_procesar_supercias(config)
        n_tablas = rpa_etapa5_cargar_sqlite(config)
        n_reportes = rpa_etapa6_generar_reportes(config)
    except Exception as e:
        rpa_log(f"[ERROR FATAL] {str(e)}", "ERROR")

    duracion = (datetime.now() - inicio).total_seconds()

    rpa_log("=" * 70)
    rpa_log("RPA MACROENTORNO ECONÓMICO - RESUMEN FINAL")
    rpa_log("=" * 70)
    rpa_log(f"  Archivos BCE procesados: {n_bce}")
    rpa_log(f"  Archivos MINEDUC procesados: {n_min}")
    rpa_log(f"  Archivos SUPERCIAS procesados: {n_sup}")
    rpa_log(f"  Tablas cargadas en SQLite: {n_tablas}")
    rpa_log(f"  Reportes generados: {n_reportes}")
    rpa_log(f"  Duración total: {duracion:.1f} segundos")
    rpa_log("=" * 70)

    rpa_guardar_log(config)


if __name__ == "__main__":
    main()
