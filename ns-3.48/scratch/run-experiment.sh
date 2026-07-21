#!/usr/bin/env bash
# run-experiment.sh -- Run baseline AODV and AI-AODV side-by-side.
# Usage:  bash scratch/run-experiment.sh [--seed 42] [--simTime 200]
#
# Requirements: run from the ns-3.48 root directory in WSL/Linux.
# Example:
#   cd ~/ns-3.48
#   bash scratch/run-experiment.sh --seed 42 --simTime 200

set -e

SEED=42
SIM_TIME=200
N_NODES=50
N_SINKS=10
W1=0.4
W2=0.4
W3=0.2
TIMEOUT=3.0

# Parse CLI overrides
while [[ $# -gt 0 ]]; do
  case $1 in
    --seed)     SEED=$2;     shift 2;;
    --simTime)  SIM_TIME=$2; shift 2;;
    --nNodes)   N_NODES=$2;  shift 2;;
    --nSinks)   N_SINKS=$2;  shift 2;;
    --w1)       W1=$2;       shift 2;;
    --w2)       W2=$2;       shift 2;;
    --w3)       W3=$2;       shift 2;;
    --timeout)  TIMEOUT=$2;  shift 2;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

echo "=== NS-3.48 MANET Routing Comparison ==="
echo "  Seed=$SEED  SimTime=${SIM_TIME}s  Nodes=$N_NODES  Sinks=$N_SINKS"
echo "  AI weights: w1=$W1 w2=$W2 w3=$W3"
echo ""

# -- Build both targets --
echo "[1/4] Building baseline (compare)..."
./ns3 build scratch/compare

echo "[2/4] Building AI-enhanced (ai-routing)..."
./ns3 build scratch/ai-routing

# -- Run baseline --
echo "[3/4] Running baseline AODV..."
./ns3 run "compare --protocol=2 \
  --CSVfileName=baseline-aodv-seed${SEED}.csv" 2>&1 | tail -5
echo "  Baseline output: baseline-aodv-seed${SEED}.csv"

# -- Run AI-enhanced --
echo "[4/4] Running AI-AODV..."
./ns3 run "ai-routing \
  --nNodes=$N_NODES \
  --nSinks=$N_SINKS \
  --simTime=$SIM_TIME \
  --seed=$SEED \
  --w1=$W1 --w2=$W2 --w3=$W3 \
  --aiRouteTimeout=$TIMEOUT \
  --CSVfileName=ai-aodv-seed${SEED}.csv" 2>&1 | tail -10
echo "  AI output: ai-aodv-seed${SEED}.csv"

echo ""
echo "=== Running comparison analysis ==="
python3 scratch/analyze-results.py \
  baseline-aodv-seed${SEED}.csv \
  ai-aodv-seed${SEED}.csv