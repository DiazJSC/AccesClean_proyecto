# Web App — Dashboard de Control de Solicitudes

Producto de datos (etapa 5) del proyecto **AccesClean**. Tablero interactivo construido con
Streamlit y Plotly que permite al equipo administrador de solicitudes de acceso anticipar la
demanda y hacer seguimiento a su desempeño operativo.

## Ejecución

Desde la raíz del proyecto, con el entorno virtual activado:

```bash
streamlit run webapp/app.py
```

El tablero queda disponible en `http://localhost:8501`.

## Contenido

El tablero se organiza en tres pestañas:

| Pestaña | Propósito |
|---|---|
| **Proyección de Demanda** | Pronóstico a 30, 90 o 120 días con intervalo de confianza y desagregación por tipo de solicitud. |
| **Desempeño Operativo** | Indicadores del histórico: cumplimiento de ANS, tiempos de atención, carga por responsable y distribución horaria. |
| **Sobre el Modelo** | Métricas de validación, ficha técnica, comparación contra el baseline y limitaciones declaradas. |

## Fuentes de datos

El tablero no reentrena el modelo: consume los archivos generados por `src/04_modelo.ipynb`.

| Archivo | Contenido |
|---|---|
| `data/trusted/datos_limpios_ml.csv` | Histórico operativo completo (5.877 solicitudes). |
| `data/surface/pronostico_120d.csv` | Pronóstico del modelo total con intervalos. |
| `data/surface/pronostico_120d_por_tipo.csv` | Pronóstico diario desagregado por tipo. |
| `data/surface/proyeccion_por_tipo.csv` | Volumen acumulado por tipo y horizonte. |
| `data/surface/metricas_finales_modelo.csv` | Métricas de validación del modelo. |

Si se modifica el modelo, basta con reejecutar `src/04_modelo.ipynb` completo
(*Restart & Run All*) para que el tablero refleje los nuevos resultados.

## Dependencias

```bash
pip install streamlit plotly
```

Ambas están incluidas en el `requirements.txt` del proyecto.
