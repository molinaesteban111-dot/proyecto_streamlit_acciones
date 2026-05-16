"""
Taller Streamlit: Predicción de Acciones sin Bola de Cristal
Universidad Externado - Valoración de Activos

La aplicación compara GBM, Heston y Saltos de Merton con backtesting por RMSE,
y proyecta rangos de precio a un mes con percentiles P5, P50 y P95.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

TRADING_DAYS = 252
DEFAULT_TICKERS = ["AAPL", "AMZN", "JPM", "XOM"]
MODEL_NAMES = ["GBM", "Heston", "Merton"]

SECTOR_MAP = {
    "AAPL": "Tecnología",
    "MSFT": "Tecnología",
    "NVDA": "Tecnología",
    "AMZN": "Consumo discrecional",
    "TSLA": "Consumo discrecional",
    "HD": "Consumo discrecional",
    "JPM": "Financiero",
    "BAC": "Financiero",
    "GS": "Financiero",
    "JNJ": "Salud",
    "PFE": "Salud",
    "UNH": "Salud",
    "XOM": "Energía",
    "CVX": "Energía",
    "CAT": "Industrial",
    "GE": "Industrial",
    "BA": "Industrial",
}


@dataclass
class SimulationResult:
    paths: pd.DataFrame
    params: Dict[str, float]


def normalize_tickers(raw_text: str) -> List[str]:
    """Convierte una caja de texto en una lista limpia de tickers."""
    tickers = [t.strip().upper() for t in raw_text.replace(";", ",").split(",")]
    tickers = [t for t in tickers if t]
    return list(dict.fromkeys(tickers))


@st.cache_data(ttl=3600, show_spinner=False)
def download_prices(tickers: Tuple[str, ...], period: str = "2y") -> pd.DataFrame:
    """Descarga precios de cierre ajustados desde Yahoo Finance mediante yfinance."""
    raw = yf.download(
        list(tickers),
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
        group_by="column",
    )

    if raw.empty:
        raise ValueError("Yahoo Finance no devolvió datos. Revisa los tickers o la conexión.")

    if isinstance(raw.columns, pd.MultiIndex):
        first_level = raw.columns.get_level_values(0)
        if "Close" in first_level:
            close = raw["Close"].copy()
        elif "Adj Close" in first_level:
            close = raw["Adj Close"].copy()
        else:
            raise ValueError("No se encontró la columna Close/Adj Close en la descarga.")
    else:
        col = "Close" if "Close" in raw.columns else "Adj Close"
        close = raw[[col]].copy()
        close.columns = [tickers[0]]

    close.index = pd.to_datetime(close.index)
    close = close.sort_index().ffill().dropna(axis=1, how="all").dropna(how="all")
    close = close[[t for t in tickers if t in close.columns]]

    if close.empty:
        raise ValueError("No quedaron series válidas después de limpiar los datos descargados.")
    return close


def log_returns(prices: pd.Series) -> pd.Series:
    """Calcula retornos logarítmicos diarios."""
    return np.log(prices / prices.shift(1)).replace([np.inf, -np.inf], np.nan).dropna()


def estimate_basic_params(returns: pd.Series) -> Dict[str, float]:
    r = returns.dropna()
    mu = float(r.mean() * TRADING_DAYS)
    sigma = float(r.std(ddof=1) * np.sqrt(TRADING_DAYS))
    return {
        "mu_anual": mu,
        "sigma_anual": max(sigma, 1e-8),
    }


def estimate_heston_params(returns: pd.Series) -> Dict[str, float]:
    r = returns.dropna()
    base = estimate_basic_params(r)
    rolling_var = r.rolling(21).var().dropna() * TRADING_DAYS

    if len(rolling_var) >= 5:
        theta = float(max(rolling_var.mean(), 1e-8))
        v0 = float(max(rolling_var.iloc[-1], 1e-8))
        var_diff = rolling_var.diff().dropna()
        xi = float(max(var_diff.std(ddof=1) * np.sqrt(TRADING_DAYS), 0.05))
        xi = min(xi, 2.0)

        aligned = pd.concat([r, rolling_var.diff()], axis=1).dropna()
        rho = float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1])) if len(aligned) > 5 else -0.30
        if np.isnan(rho):
            rho = -0.30
        rho = float(np.clip(rho, -0.95, 0.95))
    else:
        theta = base["sigma_anual"] ** 2
        v0 = theta
        xi = 0.30
        rho = -0.30

    return {
        "mu_anual": base["mu_anual"],
        "v0": v0,
        "kappa": 2.0,
        "theta": theta,
        "xi": xi,
        "rho": rho,
    }


def estimate_merton_params(returns: pd.Series) -> Dict[str, float]:
    r = returns.dropna()
    base = estimate_basic_params(r)

    center = r.mean()
    std = max(r.std(ddof=1), 1e-8)
    jump_mask = (r - center).abs() > 2.5 * std

    # Si hay pocos saltos extremos, se toma el 5% de mayores desviaciones como proxy.
    if jump_mask.sum() < 3 and len(r) >= 50:
        threshold = (r - center).abs().quantile(0.95)
        jump_mask = (r - center).abs() >= threshold

    jumps = r[jump_mask]
    diffusion = r[~jump_mask]
    years = max(len(r) / TRADING_DAYS, 1e-8)

    lambda_anual = float(max(len(jumps) / years, 0.01))
    mu_j = float(jumps.mean()) if len(jumps) > 0 else 0.0
    sigma_j = float(jumps.std(ddof=1)) if len(jumps) > 1 else float(std * 0.50)
    sigma_core = float(diffusion.std(ddof=1) * np.sqrt(TRADING_DAYS)) if len(diffusion) > 5 else base["sigma_anual"]

    return {
        "mu_anual": base["mu_anual"],
        "sigma_anual": max(sigma_core, 1e-8),
        "lambda_anual": lambda_anual,
        "mu_salto": mu_j,
        "sigma_salto": max(sigma_j, 1e-8),
        "saltos_detectados": int(len(jumps)),
    }


def _as_paths_df(paths: np.ndarray, index: pd.Index | None = None) -> pd.DataFrame:
    if index is None:
        index = pd.RangeIndex(1, paths.shape[0] + 1, name="día")
    return pd.DataFrame(paths, index=index, columns=[f"sim_{i+1}" for i in range(paths.shape[1])])


def simulate_gbm(
    s0: float,
    returns: pd.Series,
    horizon: int,
    n_sims: int,
    seed: int,
    index: pd.Index | None = None,
) -> SimulationResult:
    params = estimate_basic_params(returns)
    rng = np.random.default_rng(seed)
    dt = 1 / TRADING_DAYS

    z = rng.normal(size=(horizon, n_sims))
    shocks = (params["mu_anual"] - 0.5 * params["sigma_anual"] ** 2) * dt + params["sigma_anual"] * np.sqrt(dt) * z
    paths = s0 * np.exp(np.cumsum(shocks, axis=0))
    return SimulationResult(_as_paths_df(paths, index), params)


def simulate_heston(
    s0: float,
    returns: pd.Series,
    horizon: int,
    n_sims: int,
    seed: int,
    index: pd.Index | None = None,
) -> SimulationResult:
    params = estimate_heston_params(returns)
    rng = np.random.default_rng(seed)
    dt = 1 / TRADING_DAYS

    prices = np.zeros((horizon, n_sims))
    s = np.full(n_sims, s0, dtype=float)
    v = np.full(n_sims, params["v0"], dtype=float)

    for t in range(horizon):
        z_price = rng.normal(size=n_sims)
        z_var_ind = rng.normal(size=n_sims)
        z_var = params["rho"] * z_price + np.sqrt(max(1 - params["rho"] ** 2, 0)) * z_var_ind

        v_pos = np.maximum(v, 1e-10)
        s = s * np.exp((params["mu_anual"] - 0.5 * v_pos) * dt + np.sqrt(v_pos * dt) * z_price)
        v = v + params["kappa"] * (params["theta"] - v_pos) * dt + params["xi"] * np.sqrt(v_pos * dt) * z_var
        v = np.maximum(v, 1e-10)
        prices[t, :] = s

    return SimulationResult(_as_paths_df(prices, index), params)


def simulate_merton(
    s0: float,
    returns: pd.Series,
    horizon: int,
    n_sims: int,
    seed: int,
    index: pd.Index | None = None,
) -> SimulationResult:
    params = estimate_merton_params(returns)
    rng = np.random.default_rng(seed)
    dt = 1 / TRADING_DAYS

    z = rng.normal(size=(horizon, n_sims))
    n_jumps = rng.poisson(params["lambda_anual"] * dt, size=(horizon, n_sims))
    jump_z = rng.normal(size=(horizon, n_sims))
    jump_component = n_jumps * params["mu_salto"] + np.sqrt(n_jumps) * params["sigma_salto"] * jump_z

    shocks = (
        (params["mu_anual"] - 0.5 * params["sigma_anual"] ** 2) * dt
        + params["sigma_anual"] * np.sqrt(dt) * z
        + jump_component
    )
    paths = s0 * np.exp(np.cumsum(shocks, axis=0))
    return SimulationResult(_as_paths_df(paths, index), params)


SIMULATORS: Dict[str, Callable[..., SimulationResult]] = {
    "GBM": simulate_gbm,
    "Heston": simulate_heston,
    "Merton": simulate_merton,
}


def rmse(observed: pd.Series, predicted: pd.Series) -> float:
    aligned = pd.concat([observed, predicted], axis=1).dropna()
    aligned.columns = ["observed", "predicted"]
    return float(np.sqrt(np.mean((aligned["predicted"] - aligned["observed"]) ** 2)))


def percent_fmt(x: float) -> str:
    return f"{x:.2f}%"


def usd_fmt(x: float) -> str:
    return f"US$ {x:,.2f}"


def stable_seed(base_seed: int, ticker: str, model: str, extra: int = 0) -> int:
    return base_seed + sum(ord(c) for c in ticker) + 97 * MODEL_NAMES.index(model) + extra


def run_analysis(
    prices: pd.DataFrame,
    tickers: List[str],
    test_days: int,
    forecast_days: int,
    n_sims: int,
    seed: int,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Dict[str, Dict[str, SimulationResult]]]]:
    rmse_records = []
    projection_records = []
    simulations: Dict[str, Dict[str, Dict[str, SimulationResult]]] = {}

    for ticker in tickers:
        serie = prices[ticker].dropna()
        if len(serie) < test_days + 60:
            st.warning(f"{ticker}: serie insuficiente para entrenamiento y prueba. Se omite.")
            continue

        train = serie.iloc[:-test_days]
        test = serie.iloc[-test_days:]
        r_train = log_returns(train)
        r_all = log_returns(serie)
        simulations[ticker] = {"backtest": {}, "forecast": {}}

        for model in MODEL_NAMES:
            bt = SIMULATORS[model](
                s0=float(train.iloc[-1]),
                returns=r_train,
                horizon=len(test),
                n_sims=n_sims,
                seed=stable_seed(seed, ticker, model),
                index=test.index,
            )
            simulations[ticker]["backtest"][model] = bt
            mean_pred = bt.paths.mean(axis=1)
            rmse_records.append(
                {
                    "Acción": ticker,
                    "Modelo": model,
                    "RMSE": rmse(test, mean_pred),
                    "RMSE % precio": rmse(test, mean_pred) / float(test.mean()) * 100,
                }
            )

        ticker_rmse = pd.DataFrame([r for r in rmse_records if r["Acción"] == ticker])
        winning_model = ticker_rmse.sort_values("RMSE").iloc[0]["Modelo"]

        for model in MODEL_NAMES:
            fc = SIMULATORS[model](
                s0=float(serie.iloc[-1]),
                returns=r_all,
                horizon=forecast_days,
                n_sims=n_sims,
                seed=stable_seed(seed, ticker, model, extra=5000),
                index=pd.RangeIndex(1, forecast_days + 1, name="día"),
            )
            simulations[ticker]["forecast"][model] = fc

        winning_paths = simulations[ticker]["forecast"][winning_model].paths
        last_prices = winning_paths.iloc[-1]
        p5, p50, p95 = np.percentile(last_prices, [5, 50, 95])
        current_price = float(serie.iloc[-1])
        expected_return = (p50 / current_price - 1) * 100
        range_width_pct = (p95 - p5) / current_price * 100
        best_rmse = float(ticker_rmse["RMSE"].min())
        best_rmse_pct = best_rmse / current_price * 100

        projection_records.append(
            {
                "Acción": ticker,
                "Sector": SECTOR_MAP.get(ticker, "Otro / justificar"),
                "Modelo ganador": winning_model,
                "Precio actual": current_price,
                "Precio esperado P50": float(p50),
                "Rango inferior P5": float(p5),
                "Rango superior P95": float(p95),
                "Rango 5%-95%": f"{usd_fmt(p5)} - {usd_fmt(p95)}",
                "Valorización esperada %": float(expected_return),
                "Amplitud rango %": float(range_width_pct),
                "RMSE ganador": best_rmse,
                "RMSE ganador %": best_rmse_pct,
            }
        )

    rmse_df = pd.DataFrame(rmse_records)
    projection_df = pd.DataFrame(projection_records)
    return rmse_df, projection_df, simulations


def build_final_table(rmse_df: pd.DataFrame, projection_df: pd.DataFrame) -> pd.DataFrame:
    if rmse_df.empty or projection_df.empty:
        return pd.DataFrame()

    rmse_wide = rmse_df.pivot(index="Acción", columns="Modelo", values="RMSE").reset_index()
    rmse_wide = rmse_wide.rename(columns={"GBM": "RMSE GBM", "Heston": "RMSE Heston", "Merton": "RMSE Merton"})

    cols = [
        "Acción",
        "Modelo ganador",
        "Precio actual",
        "Precio esperado P50",
        "Rango inferior P5",
        "Rango superior P95",
        "Rango 5%-95%",
        "Valorización esperada %",
        "Amplitud rango %",
    ]
    final = projection_df[cols].merge(rmse_wide, on="Acción", how="left")
    ordered_cols = [
        "Acción",
        "Modelo ganador",
        "RMSE GBM",
        "RMSE Heston",
        "RMSE Merton",
        "Precio actual",
        "Precio esperado P50",
        "Rango inferior P5",
        "Rango superior P95",
        "Rango 5%-95%",
        "Valorización esperada %",
        "Amplitud rango %",
    ]
    return final[ordered_cols]


def score_allocation(projection_df: pd.DataFrame) -> pd.DataFrame:
    df = projection_df.copy()
    if df.empty:
        return df

    def normalize(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
        s = series.astype(float)
        if not higher_is_better:
            s = -s
        if abs(s.max() - s.min()) < 1e-12:
            return pd.Series(np.ones(len(s)), index=s.index)
        return (s - s.min()) / (s.max() - s.min())

    df["Puntaje valorización"] = normalize(df["Valorización esperada %"], True)
    df["Puntaje riesgo"] = normalize(df["Amplitud rango %"], False)
    df["Puntaje ajuste"] = normalize(df["RMSE ganador %"], False)
    df["Puntaje total"] = 0.40 * df["Puntaje valorización"] + 0.35 * df["Puntaje riesgo"] + 0.25 * df["Puntaje ajuste"]

    # Evita asignaciones negativas o cero absolutas por redondeos.
    raw = df["Puntaje total"].clip(lower=0.05)
    df["Asignación sugerida %"] = raw / raw.sum() * 100
    return df.sort_values("Asignación sugerida %", ascending=False)


def make_price_chart(prices: pd.DataFrame, tickers: List[str]) -> go.Figure:
    df = prices[tickers].dropna(how="all").reset_index().melt(id_vars=prices.index.name or "Date", var_name="Acción", value_name="Precio")
    date_col = df.columns[0]
    fig = px.line(df, x=date_col, y="Precio", color="Acción", title="Precio histórico de cierre ajustado")
    fig.update_layout(legend_title_text="Acción", yaxis_title="Precio", xaxis_title="Fecha")
    return fig


def make_returns_chart(serie: pd.Series, ticker: str) -> go.Figure:
    returns = log_returns(serie).reset_index()
    returns.columns = ["Fecha", "Retorno logarítmico"]
    fig = px.line(returns, x="Fecha", y="Retorno logarítmico", title=f"Retornos logarítmicos diarios - {ticker}")
    fig.update_layout(yaxis_tickformat=".2%", xaxis_title="Fecha")
    return fig


def make_simulation_chart(paths: pd.DataFrame, title: str, observed: pd.Series | None = None, max_paths: int = 80) -> go.Figure:
    fig = go.Figure()
    cols = list(paths.columns[: min(max_paths, paths.shape[1])])
    for col in cols:
        fig.add_trace(
            go.Scatter(
                x=paths.index,
                y=paths[col],
                mode="lines",
                line=dict(width=0.7),
                opacity=0.18,
                showlegend=False,
                hoverinfo="skip",
            )
        )

    mean_path = paths.mean(axis=1)
    fig.add_trace(go.Scatter(x=paths.index, y=mean_path, mode="lines", name="Promedio simulado", line=dict(width=3)))

    if observed is not None:
        fig.add_trace(go.Scatter(x=observed.index, y=observed.values, mode="lines+markers", name="Precio observado"))

    fig.update_layout(title=title, xaxis_title="Día / Fecha", yaxis_title="Precio", legend_title_text="Serie")
    return fig


def make_rmse_chart(rmse_df: pd.DataFrame) -> go.Figure:
    fig = px.bar(rmse_df, x="Acción", y="RMSE", color="Modelo", barmode="group", title="Comparación de RMSE por acción y modelo")
    fig.update_layout(yaxis_title="RMSE", xaxis_title="Acción")
    return fig


def make_projection_chart(projection_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if projection_df.empty:
        return fig

    fig.add_trace(
        go.Bar(
            x=projection_df["Acción"],
            y=projection_df["Precio esperado P50"],
            name="Precio esperado P50",
            error_y=dict(
                type="data",
                symmetric=False,
                array=projection_df["Rango superior P95"] - projection_df["Precio esperado P50"],
                arrayminus=projection_df["Precio esperado P50"] - projection_df["Rango inferior P5"],
            ),
        )
    )
    fig.update_layout(title="Rango proyectado a un mes: P5 - P50 - P95", xaxis_title="Acción", yaxis_title="Precio")
    return fig


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def render_recommendation(projection_df: pd.DataFrame) -> pd.DataFrame:
    alloc = score_allocation(projection_df)
    if alloc.empty:
        st.warning("No hay información suficiente para generar recomendación.")
        return alloc

    best_expected = projection_df.sort_values("Valorización esperada %", ascending=False).iloc[0]
    lowest_uncertainty = projection_df.sort_values("Amplitud rango %", ascending=True).iloc[0]
    highest_risk = projection_df.sort_values("Amplitud rango %", ascending=False).iloc[0]

    st.subheader("Recomendación ejecutiva para Don Rigoberto")
    st.write(
        f"Bajo el modelo con mejor desempeño en backtesting, la acción con mayor expectativa de valorización simulada es "
        f"**{best_expected['Acción']}** ({best_expected['Valorización esperada %']:.2f}%). "
        f"La menor incertidumbre relativa se observa en **{lowest_uncertainty['Acción']}** "
        f"(amplitud del rango: {lowest_uncertainty['Amplitud rango %']:.2f}%), mientras que la mayor incertidumbre se observa en "
        f"**{highest_risk['Acción']}** ({highest_risk['Amplitud rango %']:.2f}%)."
    )
    st.warning(
        "Esta recomendación no promete rentabilidades. Comunica escenarios simulados con base en datos históricos, "
        "backtesting y supuestos estadísticos. Los precios reales pueden cambiar por noticias, tasas, resultados financieros, "
        "liquidez y eventos no capturados por los modelos."
    )

    cols = ["Acción", "Modelo ganador", "Valorización esperada %", "Amplitud rango %", "RMSE ganador %", "Asignación sugerida %"]
    st.dataframe(alloc[cols].style.format({
        "Valorización esperada %": "{:.2f}%",
        "Amplitud rango %": "{:.2f}%",
        "RMSE ganador %": "{:.2f}%",
        "Asignación sugerida %": "{:.2f}%",
    }), use_container_width=True)
    return alloc


def main() -> None:
    st.set_page_config(page_title="Predicción de Acciones sin Bola de Cristal", layout="wide")

    st.title("Predicción de Acciones sin Bola de Cristal")
    st.caption("GBM vs. Heston vs. Saltos de Merton | Backtesting con RMSE | Proyección a 21 días bursátiles")

    with st.sidebar:
        st.header("Parámetros del análisis")
        team_name = st.text_input("Nombre del equipo", value="Equipo Don Rigoberto")
        ticker_text = st.text_input("4 tickers separados por coma", value=", ".join(DEFAULT_TICKERS))
        period = st.selectbox("Ventana histórica", options=["2y", "3y", "5y"], index=0)
        test_days = st.slider("Ventana de prueba / backtesting", min_value=10, max_value=63, value=21, step=1)
        forecast_days = st.slider("Horizonte de proyección", min_value=10, max_value=63, value=21, step=1)
        n_sims = st.slider("Simulaciones Monte Carlo", min_value=1000, max_value=5000, value=1000, step=500)
        seed = st.number_input("Semilla aleatoria", min_value=1, value=2026, step=1)
        run_button = st.button("Ejecutar análisis", type="primary")

    st.markdown(f"**Equipo:** {team_name}")
    tickers = normalize_tickers(ticker_text)

    if len(tickers) != 4:
        st.error("El taller pide exactamente 4 acciones. Ingresa 4 tickers separados por coma.")
        st.stop()

    st.write(
        "Acciones seleccionadas: "
        + ", ".join([f"**{t}** ({SECTOR_MAP.get(t, 'sector por justificar')})" for t in tickers])
    )

    try:
        with st.spinner("Descargando precios y ejecutando simulaciones..."):
            prices = download_prices(tuple(tickers), period=period)
            missing = [t for t in tickers if t not in prices.columns]
            if missing:
                st.error(f"No se encontraron datos válidos para: {', '.join(missing)}")
                st.stop()
            rmse_df, projection_df, simulations = run_analysis(prices, tickers, test_days, forecast_days, n_sims, int(seed))
    except Exception as exc:
        st.exception(exc)
        st.stop()

    if rmse_df.empty or projection_df.empty:
        st.error("No fue posible construir los resultados. Revisa la calidad de los datos descargados.")
        st.stop()

    final_table = build_final_table(rmse_df, projection_df)

    st.header("1. Datos históricos y retornos")
    st.plotly_chart(make_price_chart(prices, tickers), use_container_width=True)

    tabs = st.tabs(tickers)
    for tab, ticker in zip(tabs, tickers):
        with tab:
            st.plotly_chart(make_returns_chart(prices[ticker].dropna(), ticker), use_container_width=True)
            st.write("Últimos precios disponibles")
            st.dataframe(prices[[ticker]].tail(10), use_container_width=True)

    st.header("2. Backtesting y RMSE")
    st.dataframe(rmse_df.style.format({"RMSE": "{:.4f}", "RMSE % precio": "{:.2f}%"}), use_container_width=True)
    st.plotly_chart(make_rmse_chart(rmse_df), use_container_width=True)

    st.header("3. Tabla final de resultados")
    st.dataframe(final_table.style.format({
        "RMSE GBM": "{:.4f}",
        "RMSE Heston": "{:.4f}",
        "RMSE Merton": "{:.4f}",
        "Precio actual": "US$ {:,.2f}",
        "Precio esperado P50": "US$ {:,.2f}",
        "Rango inferior P5": "US$ {:,.2f}",
        "Rango superior P95": "US$ {:,.2f}",
        "Valorización esperada %": "{:.2f}%",
        "Amplitud rango %": "{:.2f}%",
    }), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button("Descargar tabla RMSE CSV", data=to_csv_bytes(rmse_df), file_name="tabla_rmse.csv", mime="text/csv")
    with c2:
        st.download_button("Descargar tabla proyección CSV", data=to_csv_bytes(final_table), file_name="tabla_proyeccion.csv", mime="text/csv")

    st.header("4. Proyección a un mes")
    st.plotly_chart(make_projection_chart(projection_df), use_container_width=True)

    selected_ticker = st.selectbox("Selecciona una acción para ver simulaciones", tickers)
    selected_phase = st.radio("Tipo de visualización", ["Backtesting", "Proyección"], horizontal=True)

    if selected_phase == "Backtesting":
        observed_test = prices[selected_ticker].dropna().iloc[-test_days:]
        sim_tabs = st.tabs(MODEL_NAMES)
        for tab, model in zip(sim_tabs, MODEL_NAMES):
            with tab:
                st.plotly_chart(
                    make_simulation_chart(
                        simulations[selected_ticker]["backtest"][model].paths,
                        title=f"{selected_ticker} - Backtesting con {model}",
                        observed=observed_test,
                    ),
                    use_container_width=True,
                )
    else:
        sim_tabs = st.tabs(MODEL_NAMES)
        for tab, model in zip(sim_tabs, MODEL_NAMES):
            with tab:
                st.plotly_chart(
                    make_simulation_chart(
                        simulations[selected_ticker]["forecast"][model].paths,
                        title=f"{selected_ticker} - Proyección a {forecast_days} días con {model}",
                    ),
                    use_container_width=True,
                )

    st.header("5. Decisión de inversión")
    allocation_df = render_recommendation(projection_df)
    st.download_button(
        "Descargar asignación sugerida CSV",
        data=to_csv_bytes(allocation_df),
        file_name="asignacion_sugerida.csv",
        mime="text/csv",
    )

    with st.expander("Parámetros estimados por modelo"):
        rows = []
        for ticker in tickers:
            for phase in ["backtest", "forecast"]:
                for model in MODEL_NAMES:
                    params = simulations[ticker][phase][model].params
                    rows.append({"Acción": ticker, "Fase": phase, "Modelo": model, **params})
        params_df = pd.DataFrame(rows)
        st.dataframe(params_df, use_container_width=True)
        st.download_button("Descargar parámetros CSV", data=to_csv_bytes(params_df), file_name="parametros_modelos.csv", mime="text/csv")

    st.caption(
        "Nota metodológica: GBM usa tendencia y volatilidad constantes; Heston permite varianza estocástica; "
        "Merton incorpora saltos aleatorios. El modelo ganador por acción es el de menor RMSE en la ventana de prueba."
    )


if __name__ == "__main__":
    main()
