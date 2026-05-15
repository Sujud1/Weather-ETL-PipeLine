"""
dashboard.py
------------
Step 4 of the ETL Pipeline — Visualize
Reads data from the SQLite database and generates a
multi-chart dashboard saved as a PNG report.

Author: Sujud Alatrash
"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Patch
import os
from datetime import datetime


# ── Config ────────────────────────────────────────────────────────────────────

DB_PATH     = "data/weather.db"
REPORTS_DIR = "data/reports"

COLORS = {
    "hot":        "#E8593C",
    "mild":       "#EF9F27",
    "cold":       "#378ADD",
    "background": "#F8F8F6",
    "panel":      "#FFFFFF",
    "text":       "#2C2C2A",
    "subtext":    "#5F5E5A",
    "grid":       "#E8E8E4",
}

CATEGORY_COLORS = {
    "Hot":  COLORS["hot"],
    "Mild": COLORS["mild"],
    "Cold": COLORS["cold"],
}


# ── Data Loading ───────────────────────────────────────────────────────────────

def load_data(db_path: str = DB_PATH) -> pd.DataFrame:
    """Load the latest weather reading per city from SQLite."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT * FROM weather_readings ORDER BY fetched_at DESC, temp_c DESC;",
        conn
    )
    conn.close()

    if df.empty:
        raise ValueError("No data in database. Run the full pipeline first.")

    df["fetched_at"] = pd.to_datetime(df["fetched_at"], format='ISO8601')
    df = (
        df.sort_values("fetched_at", ascending=False)
          .groupby("city", as_index=False)
          .first()
          .sort_values("temp_c", ascending=False)
          .reset_index(drop=True)
    )

    print(f"  Loaded {len(df)} cities from database")
    return df


# ── Chart Functions ────────────────────────────────────────────────────────────

def chart_temperature_bar(ax, df):
    """Horizontal bar chart: temperature per city, colored by category."""
    bar_colors = df["temp_category"].map(CATEGORY_COLORS).fillna(COLORS["mild"])
    bars = ax.barh(df["city"], df["temp_c"], color=bar_colors,
                   edgecolor="none", height=0.6)

    for bar, val in zip(bars, df["temp_c"]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}°C", va="center", ha="left",
                fontsize=9, color=COLORS["text"])

    ax.set_title("Temperature by City", fontsize=11,
                 fontweight="bold", color=COLORS["text"], pad=10)
    ax.set_xlabel("°C", fontsize=9, color=COLORS["subtext"])
    ax.set_xlim(0, df["temp_c"].max() + 8)
    ax.invert_yaxis()
    ax.grid(axis="x", color=COLORS["grid"], linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(labelsize=9)


def chart_humidity_scatter(ax, df):
    """Scatter: temperature vs humidity. Bubble size = wind speed."""
    for _, row in df.iterrows():
        color = CATEGORY_COLORS.get(row["temp_category"], COLORS["mild"])
        size  = max(row["wind_speed_ms"] * 20, 40) if pd.notna(row["wind_speed_ms"]) else 40
        ax.scatter(row["temp_c"], row["humidity_pct"],
                   s=size, color=color, alpha=0.8,
                   edgecolors="white", linewidths=0.8)
        ax.annotate(row["city"], (row["temp_c"], row["humidity_pct"]),
                    textcoords="offset points", xytext=(6, 4),
                    fontsize=8, color=COLORS["subtext"])

    ax.set_title("Temperature vs Humidity\n(bubble size = wind speed)",
                 fontsize=11, fontweight="bold", color=COLORS["text"], pad=10)
    ax.set_xlabel("Temperature (°C)", fontsize=9, color=COLORS["subtext"])
    ax.set_ylabel("Humidity (%)",     fontsize=9, color=COLORS["subtext"])
    ax.grid(color=COLORS["grid"], linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=9)


def chart_daylight_bar(ax, df):
    """Vertical bar chart: daylight hours per city."""
    df_sorted = df.sort_values("daylight_hours", ascending=False)
    ax.bar(df_sorted["city"], df_sorted["daylight_hours"],
           color=COLORS["mild"], edgecolor="none", width=0.6)
    ax.axhline(12, color=COLORS["subtext"], linewidth=1,
               linestyle="--", alpha=0.6, label="12h equinox")

    for i, (_, row) in enumerate(df_sorted.iterrows()):
        ax.text(i, row["daylight_hours"] + 0.1, f"{row['daylight_hours']:.1f}h",
                ha="center", va="bottom", fontsize=8, color=COLORS["text"])

    ax.set_title("Daylight Hours", fontsize=11,
                 fontweight="bold", color=COLORS["text"], pad=10)
    ax.set_ylabel("Hours", fontsize=9, color=COLORS["subtext"])
    ax.set_ylim(0, df["daylight_hours"].max() + 2)
    ax.tick_params(axis="x", labelrotation=20, labelsize=8)
    ax.tick_params(axis="y", labelsize=9)
    ax.legend(fontsize=8, frameon=False)
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)


def chart_conditions_pie(ax, df):
    """Pie chart: distribution of weather conditions."""
    counts = df["weather_main"].value_counts()
    pie_colors = [COLORS["cold"], COLORS["mild"], COLORS["hot"],
                  "#9FE1CB", "#B5D4F4"][:len(counts)]

    wedges, texts, autotexts = ax.pie(
        counts.values, labels=counts.index, autopct="%1.0f%%",
        colors=pie_colors, startangle=90, pctdistance=0.75,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5}
    )
    for t in texts:
        t.set_fontsize(9); t.set_color(COLORS["text"])
    for t in autotexts:
        t.set_fontsize(8); t.set_color(COLORS["text"])

    ax.set_title("Weather Conditions", fontsize=11,
                 fontweight="bold", color=COLORS["text"], pad=10)


def chart_stats_table(ax, df):
    """Summary stats table spanning the full bottom row."""
    ax.axis("off")

    stats = {
        "Hottest city":    f"{df.iloc[0]['city']}  {df.iloc[0]['temp_c']:.1f}°C",
        "Coldest city":    f"{df.iloc[-1]['city']}  {df.iloc[-1]['temp_c']:.1f}°C",
        "Avg temperature": f"{df['temp_c'].mean():.1f}°C",
        "Avg humidity":    f"{df['humidity_pct'].mean():.1f}%",
        "Avg wind speed":  f"{df['wind_speed_ms'].mean():.1f} m/s",
        "Most daylight":   f"{df.loc[df['daylight_hours'].idxmax(), 'city']}  {df['daylight_hours'].max():.1f}h",
        "Cities tracked":  str(len(df)),
        "Last updated":    df["fetched_at"].max().strftime("%Y-%m-%d %H:%M UTC"),
    }

    table = ax.table(
        cellText=[[k, v] for k, v in stats.items()],
        colLabels=["Metric", "Value"],
        cellLoc="left", loc="center",
        bbox=[0, 0, 1, 1]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)

    for j in range(2):
        table[(0, j)].set_facecolor(COLORS["cold"])
        table[(0, j)].set_text_props(color="white", fontweight="bold")

    for i in range(1, len(stats) + 1):
        bg = "#F1EFE8" if i % 2 == 0 else COLORS["panel"]
        for j in range(2):
            table[(i, j)].set_facecolor(bg)
            table[(i, j)].set_edgecolor(COLORS["grid"])

    ax.set_title("Summary Statistics", fontsize=11,
                 fontweight="bold", color=COLORS["text"], pad=10)


# ── Main Dashboard Function ────────────────────────────────────────────────────

def visualize(db_path: str = DB_PATH, output_dir: str = REPORTS_DIR) -> str:
    """
    Main visualize function.
    Generates a 5-panel dashboard and saves it as a PNG.
    Returns the path to the saved image.
    """
    print("=" * 50)
    print("STEP 4 — VISUALIZE")
    print("=" * 50)

    df = load_data(db_path)

    # ── Layout: 2x2 grid + 1 wide bottom panel ───────────────────────────────
    fig = plt.figure(figsize=(14, 12), facecolor=COLORS["background"])
    fig.suptitle(
        "Global Weather Dashboard",
        fontsize=16, fontweight="bold", color=COLORS["text"], y=0.97
    )

    gs = gridspec.GridSpec(
        3, 2, figure=fig,
        hspace=0.45, wspace=0.35,
        top=0.92, bottom=0.08, left=0.08, right=0.96
    )

    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])
    ax5 = fig.add_subplot(gs[2, :])

    for ax in [ax1, ax2, ax3, ax4, ax5]:
        ax.set_facecolor(COLORS["panel"])

    print("  Drawing charts...")
    chart_temperature_bar(ax1, df)
    chart_humidity_scatter(ax2, df)
    chart_daylight_bar(ax3, df)
    chart_conditions_pie(ax4, df)
    chart_stats_table(ax5, df)

    # ── Shared legend ─────────────────────────────────────────────────────────
    legend_elements = [
        Patch(facecolor=COLORS["hot"],  label="Hot  (>25°C)"),
        Patch(facecolor=COLORS["mild"], label="Mild (10-25°C)"),
        Patch(facecolor=COLORS["cold"], label="Cold (<10°C)"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=3,
               fontsize=9, frameon=False, bbox_to_anchor=(0.5, 0.01))

    # ── Timestamp ─────────────────────────────────────────────────────────────
    fig.text(0.96, 0.01,
             f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
             ha="right", va="bottom", fontsize=7, color=COLORS["subtext"])

    # ── Save ──────────────────────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filepath  = os.path.join(output_dir, f"weather_dashboard_{timestamp}.png")

    plt.savefig(filepath, dpi=150, bbox_inches="tight",
                facecolor=COLORS["background"])
    plt.close()

    print(f"  Dashboard saved -> {filepath}")
    print("\nVisualize complete.")
    return filepath


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    path = visualize()
    print(f"\nOpen your dashboard: {path}")