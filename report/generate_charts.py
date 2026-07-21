#!/usr/bin/env python3
"""
generate_charts.py
==================
Generates modern, beginner-friendly, publication-quality visual charts
explaining the CS332 MANET Routing Optimization system.

Design Philosophy:
  - Rich aesthetics: Vibrant colors, dark mode contrast / sleek card layouts.
  - Beginner-friendly: Embedded callout boxes explaining exactly what percentages
    and metrics mean so anyone can understand the results instantly.
"""

import os
import csv
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Create figures directory
os.makedirs('report/figures', exist_ok=True)
ns3_dir = 'ns-3.48'

def load_csv(filepath):
    rows = []
    if not os.path.exists(filepath):
        return rows
    with open(filepath, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

# Color Palette (Modern Executive Theme)
COLOR_BASELINE  = '#2563EB'  # Royal Blue
COLOR_AI_LOW    = '#EF4444'  # Vibrant Red / Coral
COLOR_AI_TUNED  = '#10B981'  # Emerald Green
BG_COLOR        = '#F8FAFC'  # Off-white Slate
CARD_BG         = '#FFFFFF'  # White Card
TEXT_DARK       = '#0F172A'  # Slate 900

# Chart 1: Beginner-Friendly PDR Comparison Bar Chart
fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
fig.patch.set_facecolor(BG_COLOR)
ax.set_facecolor(CARD_BG)

protocols = ['Standard AODV\n(Baseline)', 'AI-AODV\n(Fast Refresh: 1.5s)', 'AI-AODV Tuned\n(Normal Refresh: 3.0s)']
pdrs = [87.2, 22.6, 69.9]
bar_colors = [COLOR_BASELINE, COLOR_AI_LOW, COLOR_AI_TUNED]

bars = ax.bar(protocols, pdrs, color=bar_colors, width=0.45, edgecolor='#334155', linewidth=1.5, zorder=3)

ax.set_ylabel('Packet Delivery Success Rate (%)', fontsize=13, fontweight='bold', color=TEXT_DARK, labelpad=10)
ax.set_title('Network Packet Delivery Success Rate (PDR) Comparison', fontsize=15, fontweight='bold', color=TEXT_DARK, pad=20)
ax.set_ylim(0, 110)
ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
ax.tick_params(colors=TEXT_DARK, labelsize=11)

# Annotate percentages on top of bars
for bar_elem in bars:
    height = bar_elem.get_height()
    ax.annotate(f'{height:.1f}%',
                xy=(bar_elem.get_x() + bar_elem.get_width() / 2, height),
                xytext=(0, 6), textcoords="offset points",
                ha='center', va='bottom', fontsize=12, fontweight='bold', color=TEXT_DARK)

# Beginner Explanatory Box (Card)
explanation_text = (
    "[BEGINNER GUIDE: WHAT DOES THIS MEAN?]\n"
    "• 87.2% Delivery means 87 out of 100 sent messages successfully reached their destination.\n"
    "• Standard AODV performs best in fixed networks because nodes stay still and paths never break.\n"
    "• AI-AODV adds adaptive routing to protect against moving nodes & battery death."
)
ax.text(0.5, 0.78, explanation_text, transform=ax.transAxes, fontsize=10,
        verticalalignment='top', horizontalalignment='center',
        bbox=dict(boxstyle='round,pad=0.8', facecolor='#EFF6FF', edgecolor='#93C5FD', alpha=0.95))

plt.tight_layout()
pdr_fig_path = 'report/figures/pdr_comparison.png'
plt.savefig(pdr_fig_path, bbox_inches='tight')
plt.close()
print(f"Saved: {pdr_fig_path}")

# Chart 2: Beginner-Friendly Time-Series Throughput Chart
fig, ax = plt.subplots(figsize=(11, 6), dpi=300)
fig.patch.set_facecolor(BG_COLOR)
ax.set_facecolor(CARD_BG)

b_rows = load_csv(os.path.join(ns3_dir, 'baseline-aodv-seed42.csv'))
ai30_rows = load_csv(os.path.join(ns3_dir, 'ai-aodv-t3.csv'))

if b_rows:
    secs = [float(r['SimulationSecond']) for r in b_rows if 'SimulationSecond' in r]
    rates = [float(r['ReceiveRate']) for r in b_rows if 'ReceiveRate' in r]
    ax.plot(secs, rates, label='Standard Baseline AODV', color=COLOR_BASELINE, linewidth=2.5, zorder=3)

if ai30_rows:
    secs_ai = [float(r['Second']) for r in ai30_rows if 'Second' in r]
    rates_ai = [float(r['RxRate_kbps']) for r in ai30_rows if 'RxRate_kbps' in r]
    ax.plot(secs_ai, rates_ai, label='AI-Enhanced AODV', color=COLOR_AI_TUNED, linewidth=2.2, linestyle='--', zorder=4)

ax.set_xlabel('Simulation Time (Seconds 0 to 200)', fontsize=12, fontweight='bold', color=TEXT_DARK, labelpad=10)
ax.set_ylabel('Network Data Speed (kbps)', fontsize=12, fontweight='bold', color=TEXT_DARK, labelpad=10)
ax.set_title('Real-Time Data Transmission Speed Over 200 Seconds', fontsize=15, fontweight='bold', color=TEXT_DARK, pad=20)
ax.legend(fontsize=11, loc='upper left', frameon=True, facecolor='#F1F5F9', edgecolor='#CBD5E1')
ax.grid(True, linestyle='--', alpha=0.5, zorder=0)
ax.tick_params(colors=TEXT_DARK, labelsize=10)

# Annotate Warmup vs Active Traffic phase
ax.axvspan(0, 100, color='#F1F5F9', alpha=0.7, zorder=1)
ax.text(50, ax.get_ylim()[1] * 0.85, "Phase 1: Warmup & Network Discovery\n(Nodes search for neighbors)",
        ha='center', va='center', fontsize=9.5, color='#475569', style='italic',
        bbox=dict(boxstyle='square,pad=0.4', facecolor='#FFFFFF', edgecolor='#CBD5E1'))

ax.text(150, ax.get_ylim()[1] * 0.85, "Phase 2: Active Data Flow\n(Messages flowing across network)",
        ha='center', va='center', fontsize=9.5, color='#1E293B', fontweight='bold',
        bbox=dict(boxstyle='square,pad=0.4', facecolor='#ECFDF5', edgecolor='#6EE7B7'))

plt.tight_layout()
ts_fig_path = 'report/figures/throughput_timeseries.png'
plt.savefig(ts_fig_path, bbox_inches='tight')
plt.close()
print(f"Saved: {ts_fig_path}")

# Chart 3: Beginner-Friendly Parameter Sensitivity (+209% Gain)
fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
fig.patch.set_facecolor(BG_COLOR)
ax.set_facecolor(CARD_BG)

timeouts = ['Fast Refresh (1.5s)\n[Causes Network Traffic Jam]', 'Tuned Refresh (3.0s)\n[Smooth & Efficient Flow]']
pdr_timeouts = [22.6, 69.9]

bars_t = ax.bar(timeouts, pdr_timeouts, color=[COLOR_AI_LOW, COLOR_AI_TUNED], width=0.42, edgecolor='#334155', linewidth=1.5, zorder=3)

ax.set_ylabel('Packet Delivery Success Rate (%)', fontsize=12, fontweight='bold', color=TEXT_DARK, labelpad=10)
ax.set_title('AI Route Refresh Setting: Why Parameter Tuning Matters', fontsize=14, fontweight='bold', color=TEXT_DARK, pad=20)
ax.set_ylim(0, 95)
ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
ax.tick_params(colors=TEXT_DARK, labelsize=10.5)

for bar_elem in bars_t:
    height = bar_elem.get_height()
    ax.annotate(f'{height:.1f}%',
                xy=(bar_elem.get_x() + bar_elem.get_width() / 2, height),
                xytext=(0, 6), textcoords="offset points",
                ha='center', va='bottom', fontsize=12, fontweight='bold', color=TEXT_DARK)

# Arrow & +209% Gain Badge
ax.annotate('+209% PDR Gain!\n(3x More Messages Delivered)',
            xy=(1, 71), xytext=(0.4, 78),
            arrowprops=dict(facecolor='#10B981', shrink=0.08, width=2, headwidth=8),
            fontsize=11, fontweight='bold', color='#065F46',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#D1FAE5', edgecolor='#34D399'))

# Beginner Explanatory Box
explanation_text_sens = (
    "[EXPLANATION: WHY DOES THIS HAPPEN?]\n"
    "• Refreshing routes too fast (1.5s) creates a 'control traffic jam' of search requests.\n"
    "• Tuning the refresh rate to 3.0s eliminates traffic jams and delivers 3x more messages!"
)
ax.text(0.5, 0.35, explanation_text_sens, transform=ax.transAxes, fontsize=10,
        verticalalignment='top', horizontalalignment='center',
        bbox=dict(boxstyle='round,pad=0.7', facecolor='#F8FAFC', edgecolor='#CBD5E1', alpha=0.95))

plt.tight_layout()
sens_fig_path = 'report/figures/timeout_sensitivity.png'
plt.savefig(sens_fig_path, bbox_inches='tight')
plt.close()
print(f"Saved: {sens_fig_path}")

print("All beginner-friendly visual charts generated successfully!")
