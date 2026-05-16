"""Descarga precios de cierre ajustado para el taller de valoración de activos.

Uso:
    python scripts/download_data.py --tickers AAPL AMZN JPM XOM --period 2y --output data/precios_acciones.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yfinance as yf


def download_prices(tickers: list[str], period: str) -> pd.DataFrame:
    data = yf.download(
        tickers,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
        group_by="column",
    )
    if data.empty:
        raise RuntimeError("No se descargaron datos. Revisa tickers, periodo o conexión.")

    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"].copy()
    else:
        close = data[["Close"]].copy()
        close.columns = tickers

    close.index.name = "Fecha"
    return close.ffill().dropna(how="all")


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga datos de Yahoo Finance para el proyecto Streamlit.")
    parser.add_argument("--tickers", nargs="+", default=["AAPL", "AMZN", "JPM", "XOM"], help="Tickers a descargar")
    parser.add_argument("--period", default="2y", choices=["2y", "3y", "5y"], help="Ventana histórica")
    parser.add_argument("--output", default="data/precios_acciones.csv", help="Ruta del archivo CSV de salida")
    args = parser.parse_args()

    tickers = [t.upper().strip() for t in args.tickers]
    prices = download_prices(tickers, args.period)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(output, encoding="utf-8-sig")
    print(f"Datos guardados en: {output.resolve()}")
    print(prices.tail())


if __name__ == "__main__":
    main()
