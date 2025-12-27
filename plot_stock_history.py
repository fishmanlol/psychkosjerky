#!/usr/bin/env python3
"""
绘制 Psych Ko's Jerky 库存变化阶梯图

使用方法:
    python3 plot_stock_history.py

依赖:
    pip install pandas matplotlib
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

HISTORY_FILE = Path("stock_history.csv")
OUTPUT_FILE = Path("stock_chart.png")


def load_data():
    """加载并处理历史数据"""
    if not HISTORY_FILE.exists():
        print(f"❌ 历史文件不存在: {HISTORY_FILE}")
        print("   请先运行 restock_monitor.py 采集数据")
        return None
    
    df = pd.read_csv(HISTORY_FILE)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def plot_step_chart(df: pd.DataFrame):
    """绘制阶梯图"""
    
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti TC', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False
    
    products = df["product_name"].unique()
    
    # 颜色方案
    colors = {
        "mild": "#2E7D32",      # 深绿
        "medium": "#F57C00",    # 橙色
        "spicy": "#C62828",     # 深红
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
            
            # 获取当前库存
            latest_qty = int(spice_df.iloc[-1]["quantity"])
            
            # 阶梯图
            ax.step(
                spice_df["timestamp"], 
                spice_df["quantity"],
                where="post",
                linewidth=2.5,
                label=f"{spice.title()}: {latest_qty}",
                color=color,
            )
            
            # 数据点标记
            ax.scatter(
                spice_df["timestamp"],
                spice_df["quantity"],
                color=color,
                s=30,
                zorder=5,
                alpha=0.7,
            )
            
            # 标记缺货点
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
                    label="缺货" if spice == "mild" else "",
                )
        
        # 样式
        ax.set_title(product, fontsize=14, fontweight="bold", pad=10)
        ax.set_ylabel("库存数量", fontsize=12)
        ax.legend(loc="upper left", framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle="--")
        ax.set_ylim(bottom=-2, top=65)
        
        # 缺货区域
        ax.axhspan(-2, 0, color="red", alpha=0.1)
        ax.axhline(y=0, color="red", linestyle="-", linewidth=1, alpha=0.5)
        
        # 低库存警戒线
        ax.axhline(y=5, color="orange", linestyle="--", linewidth=1, alpha=0.7)
        ax.text(ax.get_xlim()[1], 5, " 低库存", va="center", fontsize=9, color="orange")
    
    # X轴时间格式
    time_range = df["timestamp"].max() - df["timestamp"].min()
    if time_range.days > 7:
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        axes[-1].xaxis.set_major_locator(mdates.DayLocator(interval=1))
    elif time_range.days > 1:
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        axes[-1].xaxis.set_major_locator(mdates.HourLocator(interval=6))
    else:
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        axes[-1].xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
    
    axes[-1].set_xlabel("时间", fontsize=12)
    plt.xticks(rotation=45, ha="right")
    
    fig.suptitle(
        "Psych Ko's Jerky 库存变化追踪",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.93, hspace=0.15)
    
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"✅ 图表已保存: {OUTPUT_FILE.resolve()}")
    
    return fig


def main():
    df = load_data()
    if df is None:
        return
    
    print(f"📊 正在生成图表... (共 {len(df)} 条记录)")
    plot_step_chart(df)
    
    try:
        plt.show()
    except:
        pass


if __name__ == "__main__":
    main()
