"""
consultas_sql.py
6 consultas analiticas sobre macroentorno.db
Demuestra: JOINs, GROUP BY, subconsultas, agregaciones, HAVING, CASE
"""
import sqlite3, pandas as pd, os

DB = os.path.join("datos_macroentorno", "macroentorno.db")

consultas = {

    "1_evolucion_pib": """
        SELECT anio,
               pib_real_musd,
               pib_percapita_nominal,
               variacion_pib_pct,
               CASE
                 WHEN variacion_pib_pct > (SELECT AVG(variacion_pib_pct) FROM pib)
                      THEN 'Sobre promedio'
                 ELSE 'Bajo promedio'
               END AS clasificacion
        FROM pib
        ORDER BY anio
    """,

    "2_top_provincias_companias": """
        SELECT provincia,
               SUM(num_companias)             AS total_companias,
               ROUND(SUM(capital_total), 2)   AS capital_total_usd,
               ROUND(AVG(capital_promedio),2) AS capital_promedio_usd
        FROM supercias
        GROUP BY provincia
        ORDER BY total_companias DESC
        LIMIT 10
    """,

    "3_vab_sectorial": """
        SELECT sector,
               ROUND(SUM(vab_miles_usd), 2) AS vab_total_miles,
               ROUND(SUM(vab_miles_usd) * 100.0 /
                     (SELECT SUM(vab_miles_usd) FROM vab), 2) AS pct_participacion
        FROM vab
        GROUP BY sector
        ORDER BY vab_total_miles DESC
    """,

    "4_iee_vs_mercado": """
        SELECT i.fecha,
               i.iee_global,
               i.comercio,
               i.manufactura,
               m.precio_petroleo_wti,
               m.riesgo_pais_pb
        FROM iee i
        INNER JOIN indicadores_mercado m ON i.fecha = m.fecha
        ORDER BY i.fecha
    """,

    "5_educacion_vs_empresas": """
        SELECT e.provincia,
               SUM(e.total_estudiantes)      AS total_estudiantes,
               SUM(e.bachilleres_3ero)       AS total_bachilleres,
               COALESCE(c.total_companias,0) AS total_companias,
               COALESCE(c.capital_total,  0) AS capital_total_usd
        FROM mineduc e
        LEFT JOIN (
            SELECT provincia,
                   SUM(num_companias)           AS total_companias,
                   ROUND(SUM(capital_total), 2) AS capital_total
            FROM supercias
            GROUP BY provincia
        ) c ON UPPER(e.provincia) = UPPER(c.provincia)
        GROUP BY e.provincia
        HAVING total_estudiantes > 0
        ORDER BY total_companias DESC
    """,

    "6_perfil_provincial": """
        SELECT v.provincia,
               ROUND(SUM(v.vab_miles_usd), 2)   AS vab_total_miles,
               COUNT(DISTINCT v.sector)          AS sectores_activos,
               COALESCE(s.total_companias, 0)    AS total_companias,
               COALESCE(s.capital_total,   0)    AS capital_total_usd,
               COALESCE(edu.total_estudiantes,0) AS total_estudiantes
        FROM vab v
        LEFT JOIN (
            SELECT provincia,
                   SUM(num_companias)           AS total_companias,
                   ROUND(SUM(capital_total), 2) AS capital_total
            FROM supercias  GROUP BY provincia
        ) s   ON UPPER(v.provincia) = UPPER(s.provincia)
        LEFT JOIN (
            SELECT provincia,
                   SUM(total_estudiantes) AS total_estudiantes
            FROM mineduc  GROUP BY provincia
        ) edu ON UPPER(v.provincia) = UPPER(edu.provincia)
        GROUP BY v.provincia
        ORDER BY vab_total_miles DESC
        LIMIT 15
    """
}

def main():
    conn = sqlite3.connect(DB)
    out = os.path.join("datos_macroentorno", "reportes")
    os.makedirs(out, exist_ok=True)

    for nombre, sql in consultas.items():
        print(f"\n{'='*65}")
        print(f"  CONSULTA: {nombre}")
        print(f"{'='*65}")
        try:
            df = pd.read_sql_query(sql, conn)
            print(df.to_string(index=False))
            csv_path = os.path.join(out, f"{nombre}.csv")
            df.to_csv(csv_path, index=False)
            print(f"\n  -> Guardado en {csv_path}  ({len(df)} filas)")
        except Exception as e:
            print(f"  ERROR: {e}")

    conn.close()
    print(f"\n{'='*65}")
    print("  TODAS LAS CONSULTAS EJECUTADAS")
    print(f"  Reportes en: {out}")
    print(f"{'='*65}")

if __name__ == "__main__":
    main()
