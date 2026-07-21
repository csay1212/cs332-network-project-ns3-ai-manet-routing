#!/usr/bin/env python3
"""
analyze-results.py
==================
Reads baseline AODV CSV and AI-AODV CSV produced by compare.cc and
ai-routing.cc respectively, then prints a side-by-side comparison of:
  - Packet Delivery Ratio (PDR)
  - Average End-to-End Delay
  - Network Lifespan (time to first node death at 5% energy)
  - Total Energy Consumed

Usage:
    python3 scratch/analyze-results.py <baseline_csv> <ai_csv>
    python3 scratch/analyze-results.py baseline-aodv-seed42.csv ai-aodv-seed42.csv

Requires: Python 3.6+ with only stdlib (csv, sys, math)
"""

import csv
import sys
import math


def load_baseline(path):
    """
    Load compare.cc CSV.
    Columns: SimulationSecond, ReceiveRate, PacketsReceived,
             NumberOfSinks, RoutingProtocol, TransmissionPower
    """
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def load_ai(path):
    """
    Load ai-routing.cc CSV.
    Columns: Second, RxRate_kbps, PktsRcvd, PktsSent, AvgDelay_ms,
             MinResidualFrac, TotalEnergySpentJ, Protocol
    """
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def pdr_baseline(rows, pps=4, sim_time=200, n_sinks=10, warmup=100):
    """
    Estimate PDR for baseline.
    Traffic starts around t=100; rate is ~4 pkt/s per flow.
    """
    total_rx = sum(int(r["PacketsReceived"]) for r in rows)
    active_secs = sim_time - warmup
    total_tx = pps * active_secs * n_sinks
    return (total_rx / total_tx) if total_tx > 0 else 0.0


def pdr_ai(rows):
    """PDR from AI CSV using PktsSent column (estimated at source)."""
    total_rx = sum(int(r["PktsRcvd"]) for r in rows if r["PktsRcvd"])
    # PktsSent is constant across rows (cumulative estimate at setup)
    total_tx_vals = [int(r["PktsSent"]) for r in rows if r["PktsSent"] and int(r["PktsSent"]) > 0]
    total_tx = max(total_tx_vals) if total_tx_vals else 0
    return (total_rx / total_tx) if total_tx > 0 else 0.0


def avg_delay_ms(rows):
    """Average delay, skipping zero-delay rows (no traffic yet)."""
    vals = [float(r["AvgDelay_ms"]) for r in rows
            if r.get("AvgDelay_ms") and float(r["AvgDelay_ms"]) > 0.0]
    return (sum(vals) / len(vals)) if vals else 0.0


def energy_lifespan(rows, sim_time=200.0):
    """
    Time at which MinResidualFrac first drops below 0.05.
    Returns sim_time if it never happens (full lifespan).
    """
    for r in rows:
        frac_str = r.get("MinResidualFrac", "")
        if frac_str:
            try:
                frac = float(frac_str)
                if frac < 0.05:
                    return float(r.get("Second", sim_time))
            except ValueError:
                pass
    return sim_time


def total_energy(rows):
    """Maximum TotalEnergySpentJ seen in the AI CSV."""
    vals = [float(r["TotalEnergySpentJ"]) for r in rows
            if r.get("TotalEnergySpentJ")]
    return max(vals) if vals else 0.0


def bar(value, max_val, width=30, symbol="#"):
    if max_val == 0:
        return "[" + " " * width + "]"
    filled = int(round(value / max_val * width))
    return "[" + symbol * filled + " " * (width - filled) + "]"


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 analyze-results.py <baseline_csv> <ai_csv>")
        sys.exit(1)

    baseline_file = sys.argv[1]
    ai_file       = sys.argv[2]

    try:
        b_rows = load_baseline(baseline_file)
    except FileNotFoundError:
        print(f"ERROR: Baseline file not found: {baseline_file}")
        sys.exit(1)

    try:
        a_rows = load_ai(ai_file)
    except FileNotFoundError:
        print(f"ERROR: AI file not found: {ai_file}")
        sys.exit(1)

    # Detect sim_time from last row
    sim_time = 200.0
    if b_rows:
        try:
            sim_time = float(b_rows[-1].get("SimulationSecond", 200))
        except (ValueError, TypeError):
            pass

    # Compute metrics
    b_pdr       = pdr_baseline(b_rows, sim_time=sim_time)
    a_pdr       = pdr_ai(a_rows)

    # Baseline has no delay column; mark as N/A
    b_delay_ms  = float("nan")
    a_delay_ms  = avg_delay_ms(a_rows)

    # Baseline has no energy column; mark as N/A
    b_lifespan  = sim_time  # assume full lifespan for baseline (no energy model)
    a_lifespan  = energy_lifespan(a_rows, sim_time)

    b_energy    = float("nan")
    a_energy    = total_energy(a_rows)

    max_pdr     = max(b_pdr, a_pdr, 1e-9)
    max_lifespan = max(b_lifespan, a_lifespan, 1e-9)

    width = 60
    div   = "-" * width

    print()
    print("=" * width)
    print("  MANET Routing Comparison: Baseline AODV vs AI-AODV")
    print("=" * width)
    print(f"  Baseline CSV : {baseline_file}")
    print(f"  AI CSV       : {ai_file}")
    print(div)
    print(f"  {'Metric':<28} {'Baseline AODV':>12}   {'AI-AODV':>12}")
    print(div)

    pdr_note = ""
    if a_pdr > b_pdr:
        pdr_note = " (*)"
    print(f"  {'Packet Delivery Ratio':<28} {b_pdr:>12.3f}   {a_pdr:>12.3f}{pdr_note}")

    b_delay_str = "N/A (no tag)"
    a_delay_str = f"{a_delay_ms:>9.2f} ms"
    print(f"  {'Avg E2E Delay':<28} {b_delay_str:>12}   {a_delay_str:>12}")

    print(f"  {'Network Lifespan (s)':<28} {b_lifespan:>12.1f}   {a_lifespan:>12.1f}")

    b_energy_str = "N/A (no model)"
    a_energy_str = f"{a_energy:>9.2f} J"
    print(f"  {'Total Energy Spent':<28} {b_energy_str:>12}   {a_energy_str:>12}")

    print(div)
    print()
    print("  PDR comparison (higher = better):")
    print(f"    Baseline: {bar(b_pdr,   max_pdr)} {b_pdr:.3f}")
    print(f"    AI-AODV:  {bar(a_pdr,   max_pdr)} {a_pdr:.3f}")
    print()
    print("  Lifespan comparison (higher = better):")
    print(f"    Baseline: {bar(b_lifespan, max_lifespan)} {b_lifespan:.0f}s")
    print(f"    AI-AODV:  {bar(a_lifespan, max_lifespan)} {a_lifespan:.0f}s")
    print()

    if a_pdr > b_pdr:
        pdr_gain = (a_pdr - b_pdr) / b_pdr * 100 if b_pdr > 0 else float("inf")
        print(f"  AI-AODV PDR improvement: +{pdr_gain:.1f}% (*)")
    elif b_pdr > a_pdr:
        pdr_loss = (b_pdr - a_pdr) / b_pdr * 100
        print(f"  Baseline PDR higher by: {pdr_loss:.1f}%")
    else:
        print("  PDR: identical")

    print("=" * width)
    print()


if __name__ == "__main__":
    main()