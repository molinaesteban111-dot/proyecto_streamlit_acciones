# Taller Streamlit: Predicción de Acciones sin Bola de Cristal

Proyecto para **Valoración de Activos**. La aplicación compara tres modelos de simulación de precios de acciones:

1. Movimiento Browniano Geométrico (**GBM**)
2. Modelo de volatilidad estocástica de **Heston**
3. Modelo de saltos de **Merton**

El sistema descarga precios diarios desde Yahoo Finance mediante `yfinance`, calcula retornos logarítmicos, realiza backtesting con RMSE y proyecta rangos de precio a un mes usando percentiles P5, P50 y P95.

## Acciones incluidas por defecto

| Acción | Sector | Justificación breve |
|---|---|---|
| AAPL | Tecnología | Alta sensibilidad a expectativas de crecimiento, innovación y resultados trimestrales. |
| AMZN | Consumo discrecional | Sensible al ciclo económico, consumo y comercio electrónico. |
| JPM | Financiero | Sensible a tasas de interés, crédito y condiciones macrofinancieras. |
| XOM | Energía | Sensible a precios del petróleo y factores geopolíticos. |

La app permite cambiar los tickers, pero el taller exige exactamente 4 acciones.

## Estructura del proyecto

```text
proyecto_don_rigoberto_streamlit/
├── app.py
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml
├── scripts/
│   └── download_data.py
├── data/
│   └── .gitkeep
└── entregables/
    ├── estructura_entrega.md
    ├── guion_video_5min.md
    ├── informe_ejecutivo.md
    ├── proyeccion_template.csv
    └── resultados_rmse_template.csv
```

## Instalación

Desde la carpeta del proyecto:

```bash
python -m venv .venv
```

Activar entorno virtual:

**Windows PowerShell**

```bash
.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

Instalar librerías:

```bash
pip install -r requirements.txt
```

## Ejecución de la aplicación

```bash
streamlit run app.py
```

Luego se abre el navegador con la app. En la barra lateral puedes modificar:

- Nombre del equipo
- 4 tickers
- Ventana histórica: 2y, 3y o 5y
- Ventana de prueba para backtesting
- Horizonte de proyección
- Número de simulaciones Monte Carlo
- Semilla aleatoria

## Descargar la base de datos manualmente

La app descarga datos automáticamente. Si el profesor exige anexar la base descargada, ejecuta:

```bash
python scripts/download_data.py --tickers AAPL AMZN JPM XOM --period 2y --output data/precios_acciones.csv
```

Esto genera un CSV en la carpeta `data/`.

## Cómo se calcula el backtesting

Para cada acción:

1. Se descarga una ventana histórica mínima de dos años.
2. Se separa el último mes observado, por defecto 21 días bursátiles, como ventana de prueba.
3. Se estiman parámetros con la ventana de entrenamiento.
4. Se simulan precios para el periodo de prueba con GBM, Heston y Merton.
5. Se calcula el precio promedio simulado por día.
6. Se compara el precio observado contra el promedio simulado.
7. Se calcula RMSE.
8. El modelo con menor RMSE gana para esa acción.

## Cómo se calcula la proyección

Una vez identificado el modelo ganador por acción, se simula el próximo mes, por defecto 21 días bursátiles. El rango final se toma con percentiles:

- Rango inferior: P5
- Precio esperado: P50
- Rango superior: P95

## Entregables cubiertos

- Código de Streamlit: `app.py`
- Librerías: `requirements.txt`
- Script de descarga: `scripts/download_data.py`
- Tabla RMSE: se visualiza y descarga desde la app como `tabla_rmse.csv`
- Tabla de proyección: se visualiza y descarga desde la app como `tabla_proyeccion.csv`
- Video: guion listo en `entregables/guion_video_5min.md`
- Informe ejecutivo: `entregables/informe_ejecutivo.md`

## Advertencia ejecutiva

El proyecto no promete rentabilidades. Presenta escenarios simulados con base en supuestos estadísticos y datos históricos. Los precios reales pueden cambiar por eventos que no están capturados completamente por GBM, Heston o Merton.
