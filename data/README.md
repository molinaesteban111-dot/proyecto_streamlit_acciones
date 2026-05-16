# Carpeta de datos

La aplicación descarga datos automáticamente desde Yahoo Finance. Si necesitas anexar la base descargada, ejecuta desde la raíz del proyecto:

```bash
python scripts/download_data.py --tickers AAPL AMZN JPM XOM --period 2y --output data/precios_acciones.csv
```
