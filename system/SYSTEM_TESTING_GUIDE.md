# System Testing & Command Reference

Quick command cheatsheet for running and testing the **AI-Enhanced MANET Routing System** in `ns-3.48/ns-3.48/`.

---

## Quick Start (One-Command Test)

From `ns-3.48/ns-3.48/`:

```bash
bash scratch/run-experiment.sh --seed 42 --simTime 200
```

---

## Step-by-Step Command Guide

### 1. Build Binaries
```bash
./ns3 build scratch/compare
./ns3 build scratch/ai-routing
```

### 2. Run Baseline AODV
```bash
./ns3 run "compare --protocol=2 --CSVfileName=baseline-aodv.csv --seed=42 --simTime=200"
```

### 3. Run AI-AODV
```bash
./ns3 run "ai-routing --nNodes=50 --nSinks=10 --simTime=200 --seed=42 --w1=0.4 --w2=0.4 --w3=0.2 --aiRouteTimeout=1.5 --CSVfileName=ai-aodv.csv"
```

### 4. Analyze & Compare Metrics
```bash
python3 scratch/analyze-results.py baseline-aodv.csv ai-aodv.csv
```

---

## Customizing AI Weights

- **Hop Ratio Focus**: `w1=0.6, w2=0.2, w3=0.2`
- **Energy Focus**: `w1=0.2, w2=0.6, w3=0.2`
- **Reliability Focus**: `w1=0.2, w2=0.2, w3=0.6`

Command example:
```bash
./ns3 run "ai-routing --w1=0.2 --w2=0.6 --w3=0.2 --CSVfileName=ai-energy-focused.csv"
```

---

For full architecture details, mathematical formulas, and CSV schemas, see [system/README.md](file:///c:/Users/saych/uni/Year4/Semester%202/CS332/Project/ns-3.48/system/README.md).
