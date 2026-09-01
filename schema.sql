-- Esquema de la base de datos interna del observatorio.
-- Motor: SQLite. Un unico archivo observatorio.db versionado en el repo.
--
-- Diseno pensado para que las revisiones de datos (tipico en INDEC, que
-- republica trimestres "provisorios") no se pierdan: en vez de UPDATE sobre
-- observaciones, siempre se hace INSERT con un vintage nuevo. La vista
-- ultimo_vintage resuelve "cual es el valor vigente hoy" sin borrar el
-- historial de revisiones.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS fuentes (
    id              INTEGER PRIMARY KEY,
    nombre          TEXT NOT NULL,              -- "Secretaria de Finanzas", "INDEC", etc.
    organismo       TEXT,                        -- organismo madre, si aplica
    tipo_acceso     TEXT NOT NULL CHECK (tipo_acceso IN ('api', 'csv', 'scraping', 'manual')),
    url_base        TEXT,
    frecuencia      TEXT NOT NULL CHECK (frecuencia IN ('diaria', 'mensual', 'trimestral', 'anual', 'irregular')),
    notas           TEXT
);

CREATE TABLE IF NOT EXISTS series (
    id                  INTEGER PRIMARY KEY,
    slug                TEXT NOT NULL UNIQUE,   -- "deuda_publica_bruta", "reservas_internacionales"
    nombre              TEXT NOT NULL,
    unidad              TEXT NOT NULL,           -- "millones de USD", "% del PBI"
    metodologia         TEXT,                    -- nota libre: que incluye/excluye
    fuente_id           INTEGER NOT NULL REFERENCES fuentes(id),
    serie_padre_id      INTEGER REFERENCES series(id),  -- para indicadores derivados (ej. deficits gemelos)
    es_calculada        INTEGER NOT NULL DEFAULT 0,      -- 1 si sale de combinar otras series
    formula             TEXT                     -- solo si es_calculada=1, nota de como se deriva
);

CREATE TABLE IF NOT EXISTS observaciones (
    id                  INTEGER PRIMARY KEY,
    serie_id            INTEGER NOT NULL REFERENCES series(id),
    fecha               TEXT NOT NULL,           -- fecha del periodo, formato YYYY-MM-DD
    valor               REAL NOT NULL,
    vintage             TEXT NOT NULL,           -- fecha/hora en que el pipeline cargo este valor (ISO 8601)
    es_provisorio       INTEGER NOT NULL DEFAULT 0,
    fuente_url          TEXT,                    -- URL exacta de donde salio este numero
    UNIQUE(serie_id, fecha, vintage)
);

CREATE INDEX IF NOT EXISTS idx_obs_serie_fecha ON observaciones(serie_id, fecha);

-- Bitacora de corridas de los pipelines. La ingesta corre sola todos los dias:
-- sin este registro, un pipeline que empieza a fallar no avisa nada -- la
-- pagina se queda congelada en el ultimo dato bueno y nadie se entera.
CREATE TABLE IF NOT EXISTS ingestas (
    id              INTEGER PRIMARY KEY,
    pipeline        TEXT NOT NULL,           -- "reservas", "deuda", ...
    inicio          TEXT NOT NULL,           -- ISO 8601 UTC
    fin             TEXT,
    estado          TEXT NOT NULL CHECK (estado IN ('ok', 'error')),
    filas_nuevas    INTEGER NOT NULL DEFAULT 0,  -- observaciones nuevas o revisadas
    mensaje         TEXT                     -- el traceback, si estado='error'
);

CREATE INDEX IF NOT EXISTS idx_ingestas_pipeline ON ingestas(pipeline, inicio);

-- Ultima corrida de cada pipeline: es lo que alimenta el "Datos actualizados
-- al ..." del encabezado del sitio.
CREATE VIEW IF NOT EXISTS ultima_ingesta AS
SELECT i.*
FROM ingestas i
INNER JOIN (
    SELECT pipeline, MAX(inicio) AS max_inicio
    FROM ingestas
    GROUP BY pipeline
) u ON i.pipeline = u.pipeline AND i.inicio = u.max_inicio;

-- Vista: para cada (serie, fecha) devuelve solo la carga mas reciente
-- (el "valor vigente hoy"), descartando vintages viejos.
CREATE VIEW IF NOT EXISTS ultimo_vintage AS
SELECT o.*
FROM observaciones o
INNER JOIN (
    SELECT serie_id, fecha, MAX(vintage) AS max_vintage
    FROM observaciones
    GROUP BY serie_id, fecha
) mv ON o.serie_id = mv.serie_id AND o.fecha = mv.fecha AND o.vintage = mv.max_vintage;

-- Vista de conveniencia: serie + fuente + ultimo valor vigente, todo junto,
-- pensada para alimentar directo el export a JSON.
CREATE VIEW IF NOT EXISTS series_con_datos AS
SELECT
    s.slug,
    s.nombre,
    s.unidad,
    s.metodologia,
    f.nombre AS fuente_nombre,
    f.tipo_acceso,
    uv.fecha,
    uv.valor,
    uv.es_provisorio,
    uv.fuente_url,
    uv.vintage
FROM series s
JOIN fuentes f ON f.id = s.fuente_id
JOIN ultimo_vintage uv ON uv.serie_id = s.id
ORDER BY s.slug, uv.fecha;

-- Semilla minima: las fuentes que ya identificamos en el chat.
INSERT OR IGNORE INTO fuentes (id, nombre, organismo, tipo_acceso, url_base, frecuencia) VALUES
    (1, 'Estadisticas BCRA / datos.gob.ar', 'BCRA', 'api', 'https://apis.datos.gob.ar/series/api/series/', 'diaria'),
    (2, 'Boletin mensual de deuda', 'Secretaria de Finanzas', 'scraping', 'https://www.argentina.gob.ar/economia/finanzas/datos-mensuales', 'mensual'),
    (3, 'Resultado del Sector Publico Nacional', 'Secretaria de Hacienda', 'scraping', 'https://www.argentina.gob.ar', 'mensual'),
    (4, 'Serie anual gastos/recursos/PBI', 'Subsecretaria de Presupuesto', 'csv', 'https://dgsiaf-repo.mecon.gob.ar/repository/pa/datasets/serie_pib_anual.csv', 'anual'),
    (5, 'Balanza de pagos', 'INDEC', 'scraping', 'https://www.indec.gob.ar', 'trimestral'),
    (6, 'Informe de recaudacion', 'IARAF (sobre datos ARCA)', 'manual', 'https://www.iaraf.org', 'mensual'),
    (7, 'API de series de tiempo', 'datos.gob.ar (INDEC / BCRA / Hacienda)', 'api', 'https://apis.datos.gob.ar/series/api/', 'diaria'),
    (8, 'Datos trimestrales de la deuda', 'Secretaria de Finanzas', 'scraping', 'https://www.argentina.gob.ar/economia/finanzas/datos-trimestrales-de-la-deuda', 'trimestral'),
    (9, 'Bluelytics (dolar blue)', 'fuente no oficial', 'api', 'https://api.bluelytics.com.ar/v2/', 'diaria');

INSERT OR IGNORE INTO series (id, slug, nombre, unidad, fuente_id, es_calculada, metodologia) VALUES
    (1, 'reservas_internacionales', 'Reservas internacionales del BCRA', 'millones de USD', 1, 0, NULL),
    (2, 'deuda_publica_bruta', 'Deuda publica bruta', 'millones de USD', 2, 0, NULL),
    (3, 'resultado_primario', 'Resultado primario del SPN', 'miles de millones de ARS', 3, 0, NULL),
    (4, 'resultado_financiero', 'Resultado financiero del SPN', 'miles de millones de ARS', 3, 0, NULL),
    (5, 'gasto_nacion', 'Erogaciones primarias del SPN', 'miles de millones de ARS', 3, 0, NULL),
    (6, 'cuenta_corriente', 'Saldo de cuenta corriente', 'millones de USD', 5, 0, NULL),
    (7, 'deficit_gemelos_fiscal', 'Resultado primario anual, % PBI', '% del PBI', 3, 0, NULL),
    (8, 'deuda_externa_bruta', 'Deuda externa bruta', 'millones de USD', 5, 0, NULL),
    (9, 'presion_tributaria', 'Presion tributaria efectiva nacional', '% del PBI', 6, 0, NULL),
    (10, 'deuda_consolidada', 'Deuda bruta + pasivos remunerados BCRA', 'millones de USD', 2, 1,
        'CALCULO PROPIO anual: deuda publica bruta + pasivos remunerados del BCRA (Leliq + pases + titulos), al TC oficial de cierre de anio. NO resta las tenencias intra-sector publico (Letras Intransferibles, Adelantos Transitorios) porque ese dato no se publica como serie limpia: es una aproximacion, no la cifra exacta de Chequeado.'),
    (11, 'deuda_neta', 'Deuda consolidada neta de reservas', 'millones de USD', 2, 1,
        'CALCULO PROPIO anual: deuda_consolidada menos reservas internacionales del BCRA. Mismo limite que la consolidada.'),
    (12, 'cartera_cer', 'Deuda en pesos ajustable por CER', '% de la deuda en pesos', 8, 0,
        'Hoja A.1.4 del boletin trimestral: deuda en moneda local ajustable por CER / total moneda local, corte anual (31/12) desde 2014.'),
    (13, 'cartera_tasa_fija', 'Deuda en pesos NO ajustable por CER', '% de la deuda en pesos', 8, 0,
        'Hoja A.1.4: deuda en moneda local no ajustable por CER (tasa fija + tasa cero + variable) / total moneda local. Junto con cartera_cer suma 100% de la deuda en pesos.'),
    (14, 'cartera_dolar_linked', 'Deuda en pesos dolar linked', '% de la deuda en pesos', 8, 0,
        'Corte unico jun-2025 (OPC). El boletin A.1.4 no separa el dolar linked como categoria propia, asi que esta serie NO tiene historia: queda como referencia puntual.'),
    (15, 'resultado_primario_anual_pbi', 'Resultado primario anual, % del PBI', '% del PBI', 3, 0,
        'Cifra anual oficial en % del PBI, distinta de resultado_primario (que es nominal y mensual).'),
    (16, 'cuenta_corriente_anual', 'Saldo de cuenta corriente, acumulado anual', 'millones de USD', 5, 1,
        'Suma de los 4 trimestres del ano (o cifra anual oficial de INDEC cuando esta disponible).'),
    (17, 'gasto_nacion_anual', 'Gasto primario anual del SPN (serie oficial CSV)', 'millones de ARS', 4, 0,
        'Serie anual completa desde el CSV de la Subsecretaria de Presupuesto, distinta de gasto_nacion (que son puntos mensuales verificados a mano).'),
    -- Series de apoyo: no tienen panel propio, existen para poder calcular
    -- ratios (todo lo que sea "% del PBI" necesita el PBI en la base).
    (18, 'pbi_anual', 'PBI a precios corrientes, anual', 'millones de ARS', 7, 0,
        'INDEC via API de series (9.1_PPC_2004_A_22). Base 2004: la serie no existe antes de ese anio.'),
    (19, 'recaudacion_nacional', 'Recaudacion tributaria nacional', 'millones de ARS', 7, 0,
        'Total de recaudacion (DGI + DGA + Seguridad Social), Secretaria de Hacienda via API de series (172.3_TL_RECAION_M_0_0_17). Mensual desde 1997.'),
    (20, 'presion_tributaria_nacional', 'Presion tributaria nacional (calculo propio)', '% del PBI', 7, 1,
        'CALCULO PROPIO: recaudacion nacional acumulada del anio / PBI corriente del anio. No es una serie oficial y no coincide exactamente con la estimacion de IARAF (serie presion_tributaria), que usa otra base de tributos: comparar las dos antes de citar cualquiera.'),
    -- Comercio exterior (INDEC, Intercambio Comercial Argentino), trimestral desde 1992.
    (21, 'exportaciones', 'Exportaciones totales (FOB)', 'millones de USD', 7, 0,
        'INDEC via API (74.2_IET_0_T_16). Trimestral.'),
    (22, 'importaciones', 'Importaciones totales (CIF)', 'millones de USD', 7, 0,
        'INDEC via API (74.2_IIT_0_T_25). Trimestral.'),
    -- Resultado fiscal en dolares (blue): las series ARS convertidas al blue del mes.
    (23, 'resultado_primario_usd', 'Resultado primario del SPN, en dolares blue', 'millones de USD', 3, 1,
        'CALCULO PROPIO: resultado_primario (ARS) / dolar blue promedio del mes. El blue es fuente no oficial (Bluelytics).'),
    (24, 'resultado_financiero_usd', 'Resultado financiero del SPN, en dolares blue', 'millones de USD', 3, 1,
        'CALCULO PROPIO: resultado_financiero (ARS) / dolar blue promedio del mes.'),
    -- Series de apoyo para los calculos de arriba.
    (25, 'pbi_usd_anual', 'PBI a precios corrientes, en dolares, anual', 'millones de USD', 7, 0,
        'INDEC via API (9.1_PDPC_2004_A_30). Necesaria para expresar la cuenta corriente como % del PBI.'),
    (26, 'cuenta_corriente_pbi', 'Saldo de cuenta corriente anual, % del PBI', '% del PBI', 5, 1,
        'CALCULO PROPIO: cuenta_corriente_anual (USD) / pbi_usd_anual * 100. La pata externa de los deficits gemelos.'),
    (27, 'dolar_blue', 'Dolar blue (paralelo), promedio mensual', 'ARS por USD', 9, 0,
        'Fuente NO oficial: Bluelytics. Promedio mensual del valor de venta. Diario desde 2011.'),
    (28, 'dolar_oficial', 'Dolar oficial (A3500), fin de mes', 'ARS por USD', 7, 0,
        'BCRA via API (168.1_T_CAMBI500_D_0_0_17), Comunicacion A3500. Ultimo dato habil de cada mes.'),
    (29, 'pasivos_bcra', 'Pasivos remunerados del BCRA', 'millones de ARS', 7, 1,
        'CALCULO PROPIO: suma de Leliq + pases + titulos del BCRA (series 331.1 y 300.1 de la API), fin de mes.'),
    (30, 'gasto_nacion_pbi', 'Gasto primario de la Nacion, % del PBI', '% del PBI', 4, 1,
        'CALCULO PROPIO: gasto / PBI del CSV de la Subsecretaria de Presupuesto. Cuantos puntos del PBI consume el Estado nacional.'),
    -- Apertura de la deuda bruta por residencia del ACREEDOR (hoja A.4.5 del
    -- boletin trimestral). Las dos suman el total de esa hoja.
    (31, 'deuda_no_residentes', 'Deuda bruta AC en manos de no residentes', 'millones de USD', 8, 0,
        'Hoja A.4.5 del boletin trimestral ("Por residencia del tenedor"), columna Deuda Externa, pasada de miles de millones a millones de USD. Es deuda BRUTA de la Administracion Central, EXCLUIDA la deuda elegible pendiente de reestructuracion: su total es algo menor que deuda_publica_bruta. El corte por residencia es una estimacion de Finanzas sobre las cuentas internacionales del INDEC, no un censo de tenedores. Trimestral desde 1998 (anual 1994-1997); sin apertura en 2002-03.'),
    (32, 'deuda_residentes', 'Deuda bruta AC en manos de residentes', 'millones de USD', 8, 0,
        'Hoja A.4.5, columna Deuda Interna. OJO: "residentes" incluye las tenencias del propio sector publico (ANSES/FGS, BCRA), porque Finanzas no publica el intra-sector publico como serie limpia -- misma limitacion que deuda_consolidada. Por eso esta serie NO es "deuda con terceros privados".');
