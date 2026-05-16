# Guion para video de máximo 5 minutos

## 0:00 – 0:40 | Presentación del problema y acciones

Buenos días. En este proyecto ayudamos a Don Rigoberto a evaluar cuatro acciones del mercado estadounidense usando una aplicación en Streamlit. El objetivo no es adivinar el precio exacto, sino comparar modelos de simulación, medir su desempeño con backtesting y estimar rangos razonables de precio para el próximo mes.

Seleccionamos cuatro acciones de sectores distintos: AAPL en tecnología, AMZN en consumo discrecional, JPM en financiero y XOM en energía. Esta selección permite comparar activos con diferentes fuentes de riesgo.

## 0:40 – 1:30 | Explicación breve de modelos

La aplicación compara tres modelos. Primero, el Movimiento Browniano Geométrico, o GBM, que supone una tendencia y una volatilidad constantes. Es un modelo base sencillo y útil para construir escenarios iniciales.

Segundo, el modelo de Heston, que permite que la volatilidad cambie en el tiempo. Esto es importante porque en los mercados la incertidumbre no permanece constante.

Tercero, el modelo de Saltos de Merton, que incorpora saltos aleatorios en los precios. Este modelo permite capturar movimientos bruscos generados por noticias, resultados financieros o eventos inesperados.

## 1:30 – 2:30 | Backtesting y RMSE

En la aplicación descargamos precios diarios desde Yahoo Finance mediante yfinance. Usamos una ventana histórica mínima de dos años y separamos el último mes observado como ventana de prueba.

Con la ventana de entrenamiento estimamos los parámetros de cada modelo. Luego simulamos trayectorias para el periodo de prueba y comparamos el precio observado contra el precio promedio simulado.

La métrica de evaluación es el RMSE. Para cada acción, el modelo ganador es el que obtiene el menor RMSE, porque fue el que mejor se acercó al comportamiento observado durante el backtesting.

En esta sección de la app se puede ver la tabla de RMSE por acción y modelo, junto con el gráfico comparativo.

## 2:30 – 3:40 | Proyección a un mes

Después de identificar el modelo ganador para cada acción, proyectamos el precio para el próximo mes, equivalente a aproximadamente 21 días bursátiles.

La proyección no se presenta como un único número garantizado, sino como un rango. Usamos los percentiles de las simulaciones: percentil 5 como rango inferior, percentil 50 como precio esperado y percentil 95 como rango superior.

En la app se observa la tabla de proyección, donde aparecen el precio actual, el precio esperado, el rango inferior, el rango superior y el modelo ganador para cada acción. También se visualiza el gráfico de rango proyectado.

## 3:40 – 4:40 | Recomendación de inversión

La recomendación se basa en tres criterios: expectativa de valorización, incertidumbre del rango proyectado y calidad predictiva del modelo medida por RMSE.

La acción con mayor expectativa de valorización se identifica en la tabla de decisión. La acción con menor incertidumbre es la que tiene el rango proyectado más estrecho en términos relativos. La acción con mayor riesgo es la que muestra la mayor amplitud en su rango de precios.

La aplicación genera una asignación sugerida entre las cuatro acciones. Esta asignación no depende solo del retorno esperado, sino también del riesgo y del ajuste del modelo.

## 4:40 – 5:00 | Cierre ejecutivo

Como conclusión, no prometemos rentabilidades ni afirmamos que una acción va a subir. Bajo el modelo con mejor desempeño en backtesting, mostramos escenarios posibles y rangos de precio. La decisión de inversión debe entenderse como una lectura razonable del riesgo, no como una predicción exacta.

Don Rigoberto, la tranquilidad no viene de adivinar el futuro, sino de entender mejor los escenarios posibles.
