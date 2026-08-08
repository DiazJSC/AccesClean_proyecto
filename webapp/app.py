"""
AccesClean - Dashboard de Control de Solicitudes de Acceso
Universidad Libre - Seccional Cali | Diplomado en Ciencia de Datos
(c) Juan Sebastian Diaz Campos, 2026

Producto de datos de la etapa 5. Consume:
  - data/trusted/datos_limpios_ml.csv        (histórico operativo)
  - data/surface/pronostico_120d.csv         (pronóstico del modelo total)
  - data/surface/pronostico_120d_por_tipo.csv(pronóstico desagregado por tipo)
  - data/surface/proyeccion_por_tipo.csv     (volumen acumulado por horizonte)
  - data/surface/metricas_finales_modelo.csv (métricas de validación)

Ejecutar con:  streamlit run webapp/app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Configuración general
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="AccesClean | Control de Solicitudes",
    page_icon="📊",
    layout="wide",
)

RAIZ = Path(__file__).resolve().parent.parent
TRUSTED = RAIZ / "data" / "trusted"
SURFACE = RAIZ / "data" / "surface"

AZUL = "#2E5EAA"
NARANJA = "#E8833A"
VERDE = "#3A9E6E"
ROJO = "#C4453C"
GRIS = "#8A94A6"
PALETA_TIPOS = {"DESBLOQUEO": AZUL, "CREACION": NARANJA, "OTRA SOLICITUD": VERDE}


# --------------------------------------------------------------------------
# Carga de datos
# --------------------------------------------------------------------------
@st.cache_data
def cargar_historico():
    df = pd.read_csv(
        TRUSTED / "datos_limpios_ml.csv",
        parse_dates=["Fecha_apertura", "Fecha_cierre"],
    )
    df["Fecha"] = df["Fecha_apertura"].dt.normalize()
    return df


@st.cache_data
def cargar_pronosticos():
    pronostico = pd.read_csv(SURFACE / "pronostico_120d.csv", parse_dates=["ds"])
    por_tipo = pd.read_csv(SURFACE / "pronostico_120d_por_tipo.csv", parse_dates=["ds"])
    acumulado = pd.read_csv(SURFACE / "proyeccion_por_tipo.csv")
    metricas = pd.read_csv(SURFACE / "metricas_finales_modelo.csv")
    return pronostico, por_tipo, acumulado, metricas


try:
    df = cargar_historico()
    pronostico, pronostico_tipo, acumulado_tipo, metricas = cargar_pronosticos()
except FileNotFoundError as e:
    st.error(
        f"No se encontró un archivo necesario: `{e.filename}`.\n\n"
        "Ejecuta `src/04_modelo.ipynb` completo (Restart & Run All) para regenerar "
        "los insumos en `data/surface/`."
    )
    st.stop()

ULTIMA_FECHA = df["Fecha"].max()
historico_pron = pronostico[pronostico["ds"] <= ULTIMA_FECHA]
futuro_pron = pronostico[pronostico["ds"] > ULTIMA_FECHA].reset_index(drop=True)
mae_modelo = float(metricas.loc[metricas["Métrica"] == "MAE", "Valor"].iloc[0])


# --------------------------------------------------------------------------
# Barra lateral
# --------------------------------------------------------------------------
st.sidebar.title("AccesClean")
st.sidebar.caption(" By Juan Sebastian Diaz Campos")

horizonte_label = st.sidebar.radio(
    "Horizonte de proyección",
    ["30 días", "90 días", "120 días"],
    index=0,
    help="Define el período proyectado que se muestra en la pestaña de pronóstico",
)
horizonte = int(horizonte_label.split()[0])

st.sidebar.divider()
st.sidebar.subheader("Filtros para Desempeño Operativo")

sitios = st.sidebar.multiselect(
    "Sitio", sorted(df["Sitio"].unique()), default=sorted(df["Sitio"].unique())
)
responsables = st.sidebar.multiselect(
    "Responsable de Atención",
    sorted(df["Responsable_atencion"].unique()),
    default=sorted(df["Responsable_atencion"].unique()),
)

sitios_activos = sitios or sorted(df["Sitio"].unique())
responsables_activos = responsables or sorted(df["Responsable_atencion"].unique())
df_filtrado = df[
    df["Sitio"].isin(sitios_activos) & df["Responsable_atencion"].isin(responsables_activos)
]
filtro_sin_resultados = df_filtrado.empty
if filtro_sin_resultados:
    df_filtrado = df

st.sidebar.divider()
st.sidebar.caption(
    f"**Rango del Histórico:**  \n"
    f"{df['Fecha'].min():%d/%m/%Y} → {ULTIMA_FECHA:%d/%m/%Y}  \n"
    f"**Registros Totales:** {len(df)}"
)


# --------------------------------------------------------------------------
# Encabezado
# --------------------------------------------------------------------------
st.title("Dashboard - Control de Solicitudes de Acceso")
st.caption("🎯 Objetivo: Implementar un producto de datos que permita estimar y predecir la demanda de solicitudes de acceso, identificar patrones de comportamiento y monitorear métricas de control para apoyar la planeación de la capacidad operativa.")

tab_pronostico, tab_operacion, tab_modelo = st.tabs(
    ["📈 Proyección de Demanda", "⚙️ Desempeño Operativo", "🔍 Sobre el Modelo"]
)


# --------------------------------------------------------------------------
# TAB 1 — Proyección de demanda
# --------------------------------------------------------------------------
with tab_pronostico:
    ventana = futuro_pron.head(horizonte)
    total_proyectado = int(round(ventana["yhat"].sum()))
    habiles = ventana[ventana["dia_habil"] == 1]
    promedio_habil = ventana.loc[ventana["dia_habil"] == 1, "yhat"].mean()

    st.subheader(f"Proyección a {horizonte} días")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Solicitudes proyectadas", f"{total_proyectado:,}")
    c2.metric("Promedio por día hábil", f"{promedio_habil:.1f}")
    c3.metric("Días hábiles en el período", f"{len(habiles)}")
    c4.metric(
        "Margen de error esperado",
        f"± {mae_modelo:.1f}",
        help="MAE del modelo sobre el conjunto de prueba. El error crece con el horizonte: "
        "las proyecciones a 120 días son menos precisas que las de 30 días.",
    )

    # --- Serie histórica + pronóstico ---
    st.markdown("#### Demanda diaria: histórico y proyección")

    serie_real = (
        df.groupby("Fecha").size().reset_index(name="Solicitudes").rename(columns={"Fecha": "ds"})
    )
    meses_contexto = st.select_slider(
        "Meses de histórico a mostrar",
        options=[3, 6, 12, 24],
        value=6,
        format_func=lambda m: f"{m} meses",
    )
    desde = ULTIMA_FECHA - pd.DateOffset(months=meses_contexto)
    real_vis = serie_real[serie_real["ds"] >= desde]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ventana["ds"], y=ventana["yhat_upper"],
            mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ventana["ds"], y=ventana["yhat_lower"],
            mode="lines", line=dict(width=0), fill="tonexty",
            fillcolor="rgba(232,131,58,0.20)", name="Intervalo de confianza",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=real_vis["ds"], y=real_vis["Solicitudes"],
            mode="lines", name="Demanda real", line=dict(color=AZUL, width=1.6),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ventana["ds"], y=ventana["yhat"],
            mode="lines", name="Proyección", line=dict(color=NARANJA, width=2.4),
        )
    )
    fig.add_vline(x=ULTIMA_FECHA, line_dash="dash", line_color=GRIS)
    fig.add_annotation(
        x=ULTIMA_FECHA, y=1, yref="paper", text="Hoy",
        showarrow=False, xanchor="left", font=dict(color=GRIS, size=12),
    )
    fig.update_layout(
        height=420, hovermode="x unified", margin=dict(t=20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
        xaxis_title=None, yaxis_title="Solicitudes",
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Desagregación por tipo ---
    st.markdown("#### Desagregación por tipo de solicitud")
    col_izq, col_der = st.columns([1, 1.4])

    with col_izq:
        acumulado_h = acumulado_tipo[["Tipo de solicitud", horizonte_label]].copy()
        acumulado_h = acumulado_h.rename(columns={horizonte_label: "Solicitudes"})
        fig_barras = px.bar(
            acumulado_h, x="Tipo de solicitud", y="Solicitudes",
            color="Tipo de solicitud", color_discrete_map=PALETA_TIPOS, text="Solicitudes",
        )
        fig_barras.update_traces(textposition="outside")
        fig_barras.update_layout(
            height=340, showlegend=False, margin=dict(t=20, b=10),
            xaxis_title=None, yaxis_title="Solicitudes proyectadas",
        )
        st.plotly_chart(fig_barras, use_container_width=True)

    with col_der:
        tipo_ventana = pronostico_tipo[
            pronostico_tipo["ds"].isin(ventana["ds"])
        ].copy()
        tipo_semanal = (
            tipo_ventana.set_index("ds")
            .groupby("Tipo_solicitud")["yhat"]
            .resample("W").sum().reset_index()
        )
        fig_tipos = px.line(
            tipo_semanal, x="ds", y="yhat", color="Tipo_solicitud",
            color_discrete_map=PALETA_TIPOS, markers=True,
        )
        fig_tipos.update_layout(
            height=340, margin=dict(t=20, b=10), hovermode="x unified",
            xaxis_title=None, yaxis_title="Solicitudes por semana",
            legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1, title=None),
        )
        st.plotly_chart(fig_tipos, use_container_width=True)

    st.info(
        "**¿Cómo leer esta proyección?** El modelo estima el volumen total esperado; "
        "la desagregación por tipo proviene de modelos independientes y es indicativa. "
        "Las solicitudes de `MODIFICACION` y `ELIMINACION` no se proyectan por su baja frecuencia según el histórico"
        "(<1% del volumen).",
        icon="ℹ️",
    )

    st.caption(
        "Universidad Libre - Seccional Cali | Diplomado en Ciencia de Datos | "
        "Juan Sebastian Diaz Campos, 2026"
    )

# --------------------------------------------------------------------------
# TAB 2 — Desempeño operativo
# --------------------------------------------------------------------------
with tab_operacion:
    if filtro_sin_resultados:
        st.warning(
            "La combinación de **Sitio** y **Responsable de atención** seleccionada "
            "no tiene registros. Se muestra el total sin filtrar.",
            icon="⚠️",
        )

    st.subheader("Indicadores operativos del histórico")

    cumple = (df_filtrado["Cumple_ANS"] == "SI").mean() * 100
    ans_promedio = df_filtrado["ANS_dias_laborales"].mean()
    ans_mediana = df_filtrado["ANS_dias_laborales"].median()
    fuera_horario = (df_filtrado["Apertura_fuera_horario"] == "SI").mean() * 100

    k1, k2, k3, k4 = st.columns(4)
    META_ANS = 95
    META_DIA_ANS = 2
    brecha_ans = cumple - 100
    k1.metric("Cumplimiento de ANS", f"{cumple:.1f}%",
              delta=f"{brecha_ans:.1f} vs meta ({META_ANS}%)", delta_color="normal")
    k2.metric("Tiempo promedio de atención", f"{ans_promedio:.1f} días",
              delta=f"Meta {META_DIA_ANS} días", delta_color="inverse", help="Días laborales entre apertura y cierre.")
    k3.metric("Mediana tiempo de atención", f"{ans_mediana:.0f} días",
              help="Más representativo que el promedio: hay casos atípicos de hasta 143 días.")
    k4.metric("Aperturas fuera de horario", f"{fuera_horario:.1f}%")

    st.markdown("#### Evolución del cumplimiento de ANS")
    ans_mensual = (
        df_filtrado.assign(Mes=df_filtrado["Fecha"].dt.to_period("M").dt.to_timestamp())
        .groupby("Mes")
        .agg(Cumplimiento=("Cumple_ANS", lambda s: (s == "SI").mean() * 100),
             Solicitudes=("ID_caso", "count"))
        .reset_index()
    )
    fig_ans = go.Figure()
    fig_ans.add_trace(
        go.Bar(x=ans_mensual["Mes"], y=ans_mensual["Solicitudes"],
               name="Solicitudes", marker_color="rgba(138,148,166,0.35)", yaxis="y2")
    )
    fig_ans.add_trace(
        go.Scatter(x=ans_mensual["Mes"], y=ans_mensual["Cumplimiento"],
                   name="% Cumplimiento ANS", line=dict(color=VERDE, width=2.6), mode="lines+markers")
    )
    fig_ans.update_layout(
        height=380, hovermode="x unified", margin=dict(t=20, b=10),
        yaxis=dict(title="% Cumplimiento", range=[0, 100]),
        yaxis2=dict(title="Solicitudes", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
        xaxis_title=None,
    )
    st.plotly_chart(fig_ans, use_container_width=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Carga por responsable")
        carga = (
            df_filtrado.groupby("Responsable_atencion")
            .agg(Solicitudes=("ID_caso", "count"),
                 Cumplimiento=("Cumple_ANS", lambda s: (s == "SI").mean() * 100))
            .reset_index()
            .sort_values("Solicitudes", ascending=True)
        )
        fig_carga = px.bar(
            carga, x="Solicitudes", y="Responsable_atencion", orientation="h",
            color="Cumplimiento", color_continuous_scale=["#C4453C", "#E8C33A", "#3A9E6E"],
            range_color=[40, 100], text="Solicitudes",
        )
        fig_carga.update_traces(textposition="outside")
        fig_carga.update_layout(
            height=330, margin=dict(t=20, b=10), yaxis_title=None,
            coloraxis_colorbar=dict(title="% ANS"),
        )
        st.plotly_chart(fig_carga, use_container_width=True)

    with col_b:
        st.markdown("#### Distribución en horas de apertura")
        por_hora = (
            df_filtrado.groupby("Hora_apertura").size().reindex(range(24), fill_value=0)
            .reset_index()
        )
        por_hora.columns = ["Hora", "Solicitudes"]
        fig_hora = px.bar(por_hora, x="Hora", y="Solicitudes", color_discrete_sequence=[AZUL])
        fig_hora.update_layout(
            height=330, margin=dict(t=20, b=10),
            xaxis=dict(dtick=2, title="Hora del día"), yaxis_title="Solicitudes",
        )
        st.plotly_chart(fig_hora, use_container_width=True)
        st.caption(
            "Identifica las franjas de mayor entrada de solicitudes "
            "para dimensionar la disponibilidad del equipo"
        )

    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown("#### Distribución por tipo de solicitud")
        por_tipo_hist = df_filtrado["Tipo_solicitud_1"].value_counts().reset_index()
        por_tipo_hist.columns = ["Tipo", "Solicitudes"]
        fig_tipo_hist = px.pie(
            por_tipo_hist, names="Tipo", values="Solicitudes", hole=0.45,
            color_discrete_sequence=[AZUL, NARANJA, VERDE, GRIS, ROJO],
        )
        fig_tipo_hist.update_traces(
            textfont=dict(color="white", size=13),
            insidetextfont=dict(color="white"),
            outsidetextfont=dict(color="white"),
        )
        fig_tipo_hist.update_layout(height=330, margin=dict(t=20, b=10))
        st.plotly_chart(fig_tipo_hist, use_container_width=True)

    with col_d:
        st.markdown("#### Aplicaciones con mayor demanda")
        top_apps = df_filtrado["Aplicacion"].value_counts().head(8).reset_index()
        top_apps.columns = ["Aplicación", "Solicitudes"]
        top_apps = top_apps.sort_values("Solicitudes")
        fig_apps = px.bar(
            top_apps, x="Solicitudes", y="Aplicación", orientation="h",
            color_discrete_sequence=[AZUL], text="Solicitudes",
        )
        fig_apps.update_traces(textposition="outside")
        fig_apps.update_layout(height=330, margin=dict(t=20, b=10), yaxis_title=None)
        st.plotly_chart(fig_apps, use_container_width=True)
        st.caption(
            "Identificar la distribución histórica por aplicación acumulada"
        )

    st.caption(
        "Universidad Libre - Seccional Cali | Diplomado en Ciencia de Datos | "
        "Juan Sebastian Diaz Campos, 2026"
    )

# --------------------------------------------------------------------------
# TAB 3 — Sobre el modelo
# --------------------------------------------------------------------------
with tab_modelo:
    st.subheader("Transparencia del modelo predictivo")

    col1, col2 = st.columns([1, 1.5])

    with col1:
        st.markdown("##### Métricas de validación")
        st.dataframe(metricas, hide_index=True, use_container_width=True)
        st.caption(
            "Calculadas sobre un conjunto de prueba temporal "
            "(último 20% del histórico, sin aleatorizar el orden)."
        )

    with col2:
        st.markdown("##### Ficha técnica")
        st.markdown(
            """
| Elemento | Detalle |
|---|---|
| Algoritmo | Prophet (Meta) con regresor externo |
| Variable objetivo | Solicitudes abiertas por día |
| Regresor | `es_habil` — calendario laboral de Colombia |
| Estacionalidad | Semanal y anual, modo multiplicativo |
| Validación | Split temporal 80/20 + validación cruzada *rolling origin* |
| Baseline de referencia | Repetir el valor de hace 7 días (`lag_7`) |
| Histórico de entrenamiento | 2024-05-06 a 2026-06-30 (786 días) |
            """
        )

    st.markdown("##### Desempeño frente al método ingenuo")
    st.markdown(
        """
El modelo se comparó contra un baseline que simplemente repite la demanda del mismo
día de la semana anterior. Resultados sobre el conjunto de prueba:

| Tipo de día | MAE Baseline | MAE Prophet | Mejora |
|---|---|---|---|
| Día hábil | 6.19 | 5.68 | 8.3% |
| Día no hábil | 2.44 | 1.11 | 54.7% |
| **Todos los días** | **4.91** | **4.12** | **16.2%** |

La mayor parte de la ventaja proviene del manejo del calendario operativo: el modelo
conoce los festivos de Colombia y el método ingenuo no.
        """
    )

    st.caption(
        "Universidad Libre - Seccional Cali | Diplomado en Ciencia de Datos | "
        "Juan Sebastian Diaz Campos, 2026"
    )
