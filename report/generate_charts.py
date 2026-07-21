#!/usr/bin/env python3
"""
generate_charts.py
==================
Reads baseline and AI simulation CSV outputs and generates high-resolution
publication-quality charts for the CS332 final project report.

Output images:
  - report/figures/pdr_comparison.png
  - report/figures/throughput_timeseries.png
  - report/figures/timeout_sensitivity.png
"""

import os
import csv
import matplotlib.pyplot as plt

# Styling parameters
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
colors = {'baseline': '#1f77b4', 'ai_t15': '#e377c2', 'ai_t30': '#2ca02c'}

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

# 1. Load data
baseline_path = os.path.join(ns3_dir, 'baseline-aodv-seed42.csv')
ai_t15_path   = os.path.join(ns3_dir, 'ai-aodv-seed42.csv')
ai_t30_path   = os.path.join(ns3_dir, 'ai-aodv-t3.csv')

b_rows = load_csv(baseline_path)
ai15_rows = load_csv(ai_t15_path)
ai30_rows = load_csv(ai_t30_path)

# Chart 1: PDR Comparison Bar Chart
fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
protocols = ['Baseline AODV', 'AI-AODV (t=1.5s)', 'AI-AODV (t=3.0s)']
pdrs = [0.872, 0.226, 0.699]
bar_colors = [colors['baseline'], colors['ai_t15'], colors['ai_t30']]

bars = ax.bar(protocols, pdrs, color=bar_colors, width=0.5, edgecolor='black', linewidth=1)
ax.set_ylabel('Packet Delivery Ratio (PDR)', fontsize=12, fontweight='bold')
ax.set_title('MANET Protocol Packet Delivery Ratio (PDR) Comparison', fontsize=14, fontweight='bold', pad=15)
ax.set_ylim(0, 1.05)
ax.grid(axis='y', linestyle='--', alpha=0.7)

for bar_elem in bars:
    height = bar_elem.get_height()
    ax.annotate(f'{height * 100:.1f}%',
                xy=(bar_elem.get_x() + bar_elem.get_width() / 2, height),
                xytext=(0, 5), textcoords="offset points",
                ha='center', va='bottom', fontsize=11, fontweight='bold')

plt.tight_layout()
pdr_fig_path = 'report/figures/pdr_comparison.png'
plt.savefig(pdr_fig_path)
plt.close()
print(f"Saved: {pdr_fig_path}")

# Chart 2: Throughput Time-Series Chart
fig, ax = plt.subplots(figsize=(10, 5), dpi=300)

if b_rows:
    secs = [float(r['SimulationSecond']) for r in b_rows if 'SimulationSecond' in r]
    rates = [float(r['ReceiveRate']) for r in b_rows if 'ReceiveRate' in r]
    ax.plot(secs, rates, label='Baseline AODV', color=colors['baseline'], linewidth=2)

if ai30_rows:
    secs_ai = [float(r['Second']) for r in ai30_rows if 'Second' in r]
    rates_ai = [float(r['RxRate_kbps']) for r in ai30_rows if 'RxRate_kbps' in r]
    ax.plot(secs_ai, rates_ai, label='AI-AODV (t=3.0s)', color=colors['ai_t30'], linewidth=2, linestyle='--')

ax.set_xlabel('Simulation Time (Seconds)', fontsize=12, fontweight='bold')
ax.set_ylabel('Receive Rate (kbps)', fontsize=12, fontweight='bold')
ax.set_title('Throughput Time-Series Breakdown over 200s Simulation', fontsize=14, fontweight='bold', pad=15)
ax.legend(fontsize=11, loc='upper right')
ax.grid(True, linestyle='--', alpha=0.6)

plt.tight_layout()
ts_fig_path = 'report/figures/throughput_timeseries.png'
plt.savefig(ts_fig_path)
plt.close()
print(f"Saved: {ts_fig_path}")

# Chart 3: Route Timeout Sensitivity Chart
fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
timeouts = ['1.5 Seconds', '3.0 Seconds (Default)']
pdr_timeouts = [0.226, 0.699]

bars_t = ax.bar(timeouts, pdr_timeouts, color=[colors['ai_t15'], colors['ai_t30']], width=0.4, edgecolor='black')
ax.set_ylabel('Packet Delivery Ratio (PDR)', fontsize=12, fontweight='bold')
ax.set_xlabel('AODV ActiveRouteTimeout Parameter', fontsize=12, fontweight='bold')
ax.set_title('AI-AODV Route Timeout Parameter Sensitivity (+209% PDR)', fontsize=13, fontweight='bold', pad=15)
ax.set_ylim(0, 0.9)
ax.grid(axis='y', linestyle='--', alpha=0.7)

for bar_elem in bars_t:
    height = bar_elem.get_height()
    ax.annotate(f'{height * 100:.1f}%',
                xy=(bar_elem.get_x() + bar_elem.get_width() / 2, height),
                xytext=(0, 5), textcoords="offset points",
                ha='center', va='bottom', fontsize=11, fontweight='bold')

plt.tight_layout()
sens_fig_path = 'report/figures/timeout_sensitivity.png'
plt.savefig(sens_fig_path)
plt.close()
print(f"Saved: {sens_fig_path}")
print("All charts successfully generated!")
