# Informe ejecutivo: Predicción de acciones sin bola de cristal

## 1. Contexto del problema

Don Rigoberto desea evaluar cuatro acciones del mercado estadounidense con una recomendación basada en datos, no en intuiciones. Para ello se construyó una aplicación en Streamlit que compara tres modelos de simulación de precios: Movimiento Browniano Geométrico, Heston y Saltos de Merton.

El objetivo no es predecir un precio exacto, sino estimar escenarios razonables de precio a un mes y comunicar el riesgo asociado a cada acción.

## 2. Acciones seleccionadas

| Acción | Sector | Justificación |
|---|---|---|
| AAPL | Tecnología | Empresa de alta capitalización, sensible a expectativas de crecimiento, innovación y resultados corporativos. |
| AMZN | Consumo discrecional | Expuesta al comportamiento del consumidor, comercio electrónico y ciclo económico. |
| JPM | Financiero | Representa exposición a tasas de interés, crédito y condiciones macrofinancieras. |
| XOM | Energía | Sensible a precios del petróleo, demanda energética y factores geopolíticos. |

Estas acciones representan sectores distintos, lo que evita concentrar el análisis en un solo factor de riesgo.

## 3. Datos y metodología

- Fuente de datos: Yahoo Finance mediante `yfinance`.
- Frecuencia: diaria.
- Ventana histórica: mínimo dos años.
- Ventana de prueba: último mes observado, aproximadamente 21 días bursátiles.
- Simulaciones Monte Carlo: mínimo 1.000 trayectorias por modelo y acción.
- Horizonte de proyección: 21 días bursátiles.

Para cada acción se calcularon retornos logarítmicos diarios:

```text
r_t = ln(P_t / P_{t-1})
```

Con esos retornos se estimaron los parámetros iniciales de los modelos.

## 4. Modelos utilizados

### 4.1 Movimiento Browniano Geométrico, GBM

Asume tendencia y volatilidad constantes. Es útil como modelo base, pero puede fallar cuando la volatilidad cambia abruptamente o cuando hay saltos fuertes en el precio.

### 4.2 Heston

Permite que la varianza cambie en el tiempo. Es más flexible para acciones con episodios de calma y de alta incertidumbre.

### 4.3 Saltos de Merton

Incluye saltos aleatorios para capturar eventos bruscos como anuncios corporativos, resultados financieros, noticias regulatorias o shocks de mercado.

## 5. Backtesting

La aplicación separa la serie en entrenamiento y prueba. En la prueba se simulan trayectorias con cada modelo y se compara el precio observado contra el precio promedio simulado.

La métrica usada es RMSE:

```text
RMSE = sqrt(mean((precio_simulado_promedio - precio_observado)^2))
```

El modelo ganador para cada acción es el de menor RMSE.

## 6. Proyección a un mes

Luego de elegir el modelo ganador, se simula el precio futuro a 21 días bursátiles. La proyección final se reporta así:

- Rango inferior: percentil 5, P5.
- Precio esperado: percentil 50, P50.
- Rango superior: percentil 95, P95.

## 7. Resultados finales

Después de ejecutar la app, insertar o descargar la tabla final desde Streamlit:

| Acción | Modelo ganador | RMSE GBM | RMSE Heston | RMSE Merton | Precio esperado | Rango 5%-95% |
|---|---:|---:|---:|---:|---:|---:|
| AAPL | Completar desde app | - | - | - | - | - |
| AMZN | Completar desde app | - | - | - | - | - |
| JPM | Completar desde app | - | - | - | - | - |
| XOM | Completar desde app | - | - | - | - | - |

## 8. Recomendación de inversión

La recomendación debe completarse con los resultados generados por la app:

- Acción con mejor expectativa de valorización: completar desde la app.
- Acción con menor incertidumbre: completar desde la app.
- Acción con mayor riesgo: completar desde la app.
- Asignación porcentual sugerida: completar desde la tabla `asignacion_sugerida.csv`.

Redacción sugerida:

> Bajo el modelo con mejor desempeño en backtesting, las acciones analizadas muestran escenarios diferenciados de retorno y riesgo. La acción más atractiva no se selecciona únicamente por el precio esperado, sino por el balance entre valorización simulada, amplitud del rango y calidad predictiva medida con RMSE. Se recomienda revisar la asignación sugerida por la aplicación y no interpretar estos resultados como una garantía de rentabilidad.

## 9. Advertencia sobre límites de los modelos

Los modelos usan información histórica y supuestos estadísticos. No incorporan perfectamente noticias, resultados corporativos futuros, cambios regulatorios, eventos geopolíticos ni crisis de liquidez. Por tanto, la recomendación debe entenderse como análisis de escenarios y no como predicción exacta.

## 10. Cierre ejecutivo

Don Rigoberto, no podemos prometerle el precio futuro de una acción, pero sí podemos mostrarle escenarios razonables, medir qué modelo se defendió mejor en el pasado reciente y estimar un rango de precios para tomar una decisión más informada.
