#!/usr/bin/env python3

"""
Plot Psych Ko's Jerky stock history
Usage:
    python3 plot_stock_history.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from datetime import timezone, timedelta

HISTORY_FILE = Path("stock_history.csv")
OUTPUT_FILE = Path("stock_chart.png")

# 固定使用 PST 时区 (UTC-8)
PST = timezone(timedelta(hours=-8))


def load_data():
    if not HISTORY_FILE.exists():
        print(f"Error: {HISTORY_FILE} not found")
        return None

    df = pd.read_csv(HISTORY_FILE)

    timestamps = []
    for ts_str in df["timestamp"]:
        if "+" in ts_str or "-" in ts_str[10:] or ts_str.endswith("Z"):
            # 有时区信息，转换到 PST
            dt = pd.to_datetime(ts_str)
            if dt.tzinfo is not None:
                dt = dt.tz_convert(PST)
            # 去掉时区信息，matplotlib 才能正确显示
            dt = dt.tz_localize(None)
        else:
            # 无时区信息，假设已经是 PST
            dt = pd.to_datetime(ts_str)
        timestamps.append(dt)

    df["timestamp"] = pd.to_datetime(timestamps)
    return df


def filter_last_runs(df: pd.DataFrame, runs: int = 30) -> pd.DataFrame:
    """
    只保留最近 runs 次采集批次的数据。
    一次采集会写入多行（不同产品/辣度），但 unix_ts 相同。
    """
    if df is None or df.empty:
        return df

    key = "unix_ts" if "unix_ts" in df.columns else "timestamp"
    recent_keys = (
        df[[key]]
        .dropna()
        .drop_duplicates()
        .sort_values(by=key)
        .tail(runs)[key]
        .tolist()
    )
    return df[df[key].isin(recent_keys)]


def plot_step_chart(df: pd.DataFrame):
    products = df["product_name"].unique()

    colors = {
        "mild": "#2E7D32",
        "medium": "#F57C00",
        "spicy": "#C62828",
    }

    fig, axes = plt.subplots(len(products), 1, figsize=(14, 5 * len(products)), sharex=True)
    if len(products) == 1:
        axes = [axes]

    for idx, product in enumerate(products):
        ax = axes[idx]
        product_df = df[df["product_name"] == product]

        for spice in ["mild", "medium", "spicy"]:
            spice_df = product_df[product_df["spice_level"] == spice].sort_values("timestamp")
            if spice_df.empty:
                continue

            color = colors.get(spice, "#666666")
            latest_qty = int(spice_df.iloc[-1]["quantity"])

            ax.step(
                spice_df["timestamp"],
                spice_df["quantity"],
                where="post",
                linewidth=2.5,
                label=f"{spice.title()}: {latest_qty}",
                color=color,
            )

            ax.scatter(
                spice_df["timestamp"],
                spice_df["quantity"],
                color=color,
                s=30,
                zorder=5,
                alpha=0.7,
            )

            sold_out = spice_df[spice_df["sold_out"] == True]
            if not sold_out.empty:
                ax.scatter(
                    sold_out["timestamp"],
                    sold_out["quantity"],
                    color="red",
                    s=200,
                    marker="X",
                    linewidths=2,
                    zorder=10,
                    label="Sold Out" if spice == "mild" else "",
                )

        ax.set_title(product, fontsize=14, fontweight="bold", pad=10)
        ax.set_ylabel("Stock", fontsize=12)
        ax.legend(loc="upper left", framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.set_ylim(bottom=-2, top=65)

        ax.axhspan(-2, 0, color="red", alpha=0.1)
        ax.axhline(y=0, color="red", linestyle="-", linewidth=1, alpha=0.5)

        ax.axhline(y=5, color="orange", linestyle="--", linewidth=1, alpha=0.7)
        ax.text(ax.get_xlim()[1], 5, " Low", va="center", fontsize=9, color="orange")

    time_range = df["timestamp"].max() - df["timestamp"].min()
    if time_range.days > 7:
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        axes[-1].xaxis.set_major_locator(mdates.DayLocator(interval=1))
    elif time_range.days > 1:
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        axes[-1].xaxis.set_major_locator(mdates.HourLocator(interval=6))
    elif time_range.total_seconds() > 3600:
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        axes[-1].xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
    else:
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        axes[-1].xaxis.set_major_locator(mdates.AutoDateLocator())

    axes[-1].set_xlabel("Time (PST)", fontsize=12)
    plt.xticks(rotation=45, ha="right")

    fig.suptitle(
        "Psych Ko's Jerky Stock Monitor",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )

    plt.tight_layout()
    plt.subplots_adjust(top=0.93, hspace=0.15)

    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"Chart saved: {OUTPUT_FILE.resolve()}")

    return fig


def main():
    df = load_data()
    if df is None:
        return

    # ✅ 只保留最近 30 次采集
    df = filter_last_runs(df, runs=30)

    print(f"Generating chart... ({len(df)} records after cut)")
    plot_step_chart(df)


if __name__ == "__main__":
    main()
