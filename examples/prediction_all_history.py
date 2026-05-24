#!/usr/bin/env python3
"""
prediction_all_history.py

Batch prediction example using all-history stock data fetched via akshare/baostock.
Builds on get_date_new.py data format and applies Kronos forecasting.

Usage:
    python prediction_all_history.py --symbol 000001 --days 30
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from kronos import Kronos
except ImportError:
    raise ImportError("Kronos package not found. Please install or add project root to PYTHONPATH.")


DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "all_history")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "all_history")


def ensure_dirs():
    """Create output directory if it does not exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_stock_csv(symbol: str) -> pd.DataFrame:
    """
    Load stock CSV produced by get_date_new.py.

    Expected columns: date, open, high, low, close, volume
    """
    path = os.path.join(DATA_DIR, f"{symbol}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Data file not found: {path}\n"
            f"Run get_date_new.py first to download historical data."
        )
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df = df.dropna(subset=["close"])
    return df


def prepare_inputs(df: pd.DataFrame, lookback: int = 60) -> np.ndarray:
    """
    Extract the last `lookback` closing prices as the input sequence.

    Returns a 1-D numpy array of shape (lookback,).
    """
    close_prices = df["close"].values.astype(np.float64)
    if len(close_prices) < lookback:
        raise ValueError(
            f"Not enough data: need {lookback} rows, got {len(close_prices)}."
        )
    return close_prices[-lookback:]


def run_prediction(symbol: str, forecast_days: int = 30, lookback: int = 60) -> dict:
    """
    Load data, run Kronos prediction, and return results dict.

    Returns:
        dict with keys: symbol, history_dates, history_prices,
                        future_dates, predicted_prices
    """
    df = load_stock_csv(symbol)
    input_seq = prepare_inputs(df, lookback=lookback)

    model = Kronos()
    predicted = model.predict(input_seq, steps=forecast_days)

    last_date = df["date"].iloc[-1]
    future_dates = pd.bdate_range(start=last_date + timedelta(days=1), periods=forecast_days)

    return {
        "symbol": symbol,
        "history_dates": df["date"].values[-lookback:],
        "history_prices": input_seq,
        "future_dates": future_dates,
        "predicted_prices": np.array(predicted),
    }


def plot_prediction(result: dict, save: bool = True) -> None:
    """Plot historical prices alongside Kronos forecast and optionally save."""
    symbol = result["symbol"]
    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(result["history_dates"], result["history_prices"],
            label="Historical Close", color="steelblue", linewidth=1.5)
    ax.plot(result["future_dates"], result["predicted_prices"],
            label="Kronos Forecast", color="tomato", linewidth=1.5, linestyle="--")

    # Mark the boundary
    ax.axvline(x=result["history_dates"][-1], color="gray", linestyle=":", linewidth=1)

    ax.set_title(f"Kronos Prediction — {symbol}  ({len(result['future_dates'])} trading days ahead)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    fig.autofmt_xdate()
    plt.tight_layout()

    if save:
        ensure_dirs()
        out_path = os.path.join(OUTPUT_DIR, f"{symbol}_prediction.png")
        fig.savefig(out_path, dpi=150)
        print(f"[saved] {out_path}")
    else:
        plt.show()
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Kronos all-history prediction example")
    parser.add_argument("--symbol", type=str, default="000001", help="Stock symbol (default: 000001)")
    parser.add_argument("--days", type=int, default=30, help="Forecast horizon in trading days")
    parser.add_argument("--lookback", type=int, default=60, help="Input sequence length")
    parser.add_argument("--show", action="store_true", help="Display chart instead of saving")
    args = parser.parse_args()

    print(f"Running Kronos prediction for {args.symbol} ({args.days} days ahead) ...")
    result = run_prediction(args.symbol, forecast_days=args.days, lookback=args.lookback)

    last_hist = result["history_prices"][-1]
    last_pred = result["predicted_prices"][-1]
    change_pct = (last_pred - last_hist) / last_hist * 100
    print(f"  Last historical close : {last_hist:.4f}")
    print(f"  Predicted close (t+{args.days:02d}): {last_pred:.4f}  ({change_pct:+.2f}%)")

    plot_prediction(result, save=not args.show)


if __name__ == "__main__":
    main()
