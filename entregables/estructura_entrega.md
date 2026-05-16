# Estructura sugerida para entregar el proyecto

Entrega una carpeta comprimida con estos archivos:

```text
Proyecto_Don_Rigoberto_Equipo.zip
├── app.py
├── requirements.txt
├── README.md
├── scripts/
│   └── download_data.py
├── data/
│   └── precios_acciones.csv  # opcional, se genera con el script
└── entregables/
    ├── tabla_rmse.csv         # se descarga desde la app después de ejecutarla
    ├── tabla_proyeccion.csv   # se descarga desde la app después de ejecutarla
    ├── asignacion_sugerida.csv
    ├── parametros_modelos.csv
    ├── informe_ejecutivo.md
    └── guion_video_5min.md
```

## Orden recomendado antes de entregar

1. Instalar dependencias con `pip install -r requirements.txt`.
2. Ejecutar `streamlit run app.py`.
3. Descargar desde la app:
   - `tabla_rmse.csv`
   - `tabla_proyeccion.csv`
   - `asignacion_sugerida.csv`
   - `parametros_modelos.csv`
4. Si se requiere anexar la base, ejecutar:

```bash
python scripts/download_data.py --tickers AAPL AMZN JPM XOM --period 2y --output data/precios_acciones.csv
```

5. Grabar el video de máximo 5 minutos siguiendo el guion.
6. Comprimir la carpeta final.
