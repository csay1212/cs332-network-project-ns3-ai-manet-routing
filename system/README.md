# AI-Enhanced MANET Routing System — Testing & Evaluation Guide

Welcome to the **System Testing Guide** for the **AI-Enhanced Mobile Ad-Hoc Network (MANET) Routing Optimization** project built on top of **NS-3.48**.

This guide provides a complete, step-by-step walkthrough to build, execute, evaluate, and analyze the performance of the **Baseline AODV** routing protocol versus the **AI-Enhanced AODV (`AI-AODV`)** protocol.

---

## 1. System Overview & Key Architecture

The primary goal of this testing system is to quantitatively measure performance improvements across four critical MANET metrics:

1. **Packet Delivery Ratio (PDR)** — Ratio of successfully received packets vs sent packets.
2. **Average End-to-End Delay (ms)** — Per-packet delay tracked via custom `TimestampTag`.
3. **Energy Efficiency & Consumption (Joules)** — Total energy spent by nodes using 802.11b radio energy model.
4. **Network Lifespan (seconds)** — Time elapsed until node energy reserves fall below critical thresholds (5%).

### How the AI-AODV Engine Works

The AI layer in `scratch/ai-routing.cc` operates as an application-layer multi-metric observer and route scorer:
$$\text{Cost}(\text{flow}) = w_1 \cdot \text{HopRatio} + w_2 \cdot \text{EnergyCost} + w_3 \cdot \text{LinkInstability}$$

- **Hop Ratio ($w_1 = 0.4$ default)**: Estimated minimum hop count based on node positions relative to TX range (50m).
- **Energy Cost ($w_2 = 0.4$ default)**: Dynamic tracking of residual energy fraction ($1.0 - \text{RemainingEnergy} / \text{InitialEnergy}$).
- **Link Instability ($w_3 = 0.2$ default)**: Dynamic packet delivery failure rate tracked per interval.
- **Exponential Moving Average (EMA, $\alpha = 0.2$)**: Smooths noisy wireless channel variations.
- **AODV Control Lever (`ActiveRouteTimeout`)**: Dynamically triggers route rediscovery so lower-cost, higher-energy paths are preferred.

---

## 2. Directory & Workspace Structure

```
ns-3.48/                                <--- Root Project Workspace
├── system/                             <--- System Documentation & Testing Guide
│   ├── README.md                       <--- This Testing Guide
│   └── SYSTEM_TESTING_GUIDE.md         <--- Quick Reference Guide
└── ns-3.48/                            <--- NS-3 Simulator & Source Code
    ├── scratch/
    │   ├── compare.cc                  <--- Baseline AODV Simulation
    │   ├── ai-routing.cc               <--- AI-Enhanced AODV Simulation
    │   ├── run-experiment.sh           <--- One-Shot Automated Test Script
    │   ├── analyze-results.py          <--- Python Analysis & Comparison Tool
    │   ├── manet100.csv                <--- 2D Spatial Node Topology Data
    │   └── CMakeLists.txt              <--- Scratch Build Configuration
    ├── PROJECT_LOG.md                  <--- Full Implementation & API Verification Log
    └── ns3                             <--- NS-3 Build & Runner Utility
```

---

## 3. Prerequisites & Environment Setup

Before running tests, ensure your terminal environment has the required dependencies:

- **OS**: Linux or Windows Subsystem for Linux (WSL2 / Ubuntu recommended)
- **Compiler**: GCC / G++ (supporting C++17 or later)
- **Build System**: CMake & Python 3.6+ (standard library only: `csv`, `sys`, `math`)

### Initial Terminal Navigation

Always execute all commands from inside the `ns-3.48/ns-3.48` directory:

```bash
# Navigate to the NS-3 simulation working directory
cd "c:/Users/saych/uni/Year4/Semester 2/CS332/Project/ns-3.48/ns-3.48"
# Note: In WSL or native Linux environment, use:
# cd ~/path/to/ns-3.48/ns-3.48
```

---

## 4. Step-by-Step Testing Walkthrough

Follow these sequential steps to test both baseline and AI-enhanced routing implementations.

---

### Step 1: Build the Simulation Binaries

First, compile both the baseline simulator (`compare.cc`) and the AI-enhanced simulator (`ai-routing.cc`).

```bash
# Optional: Configure NS-3 (only required if build system was reset)
./ns3 configure --enable-examples

# Build baseline simulation target
./ns3 build scratch/compare

# Build AI-enhanced simulation target
./ns3 build scratch/ai-routing
```

*Expected output: `Build finished successfully` for both targets.*

---

### Step 2: Run Baseline AODV Simulation

Execute the baseline AODV routing protocol across 50 nodes for 200 simulation seconds.

```bash
./ns3 run "compare --protocol=2 --CSVfileName=baseline-aodv.csv --seed=42 --simTime=200 --nNodes=50"
```

#### CLI Parameters Explained:
- `--protocol=2`: Selects AODV routing (1=OLSR, 2=AODV, 3=DSDV, 4=DSR).
- `--CSVfileName=baseline-aodv.csv`: File path to output per-second throughput data.
- `--seed=42`: Sets deterministic random seed for reproducible packet generation and warmup.
- `--simTime=200`: Duration of simulation in seconds (warmup: 0–100s, active traffic: 100–200s).

*Expected output file: `baseline-aodv.csv` created in `ns-3.48/ns-3.48/`.*

---

### Step 3: Run AI-Enhanced AODV Simulation

Execute the AI-AODV simulation using identical spatial topology and traffic patterns, but with the AI scoring engine active.

```bash
./ns3 run "ai-routing \
  --nNodes=50 \
  --nSinks=10 \
  --simTime=200 \
  --seed=42 \
  --w1=0.4 \
  --w2=0.4 \
  --w3=0.2 \
  --aiRouteTimeout=1.5 \
  --CSVfileName=ai-aodv.csv"
```

#### AI Parameters Explained:
- `--w1=0.4`: Weight assigned to Hop Ratio cost.
- `--w2=0.4`: Weight assigned to Node Energy depletion cost.
- `--w3=0.2`: Weight assigned to Link Instability / loss cost.
- `--aiRouteTimeout=1.5`: Active route timeout in seconds (forces faster rediscovery of degraded paths).

*Expected output file: `ai-aodv.csv` created in `ns-3.48/ns-3.48/`.*

---

### Step 4: Run Results Analysis & Comparison

Run the Python analysis script to compare the generated CSVs side-by-side:

```bash
python3 scratch/analyze-results.py baseline-aodv.csv ai-aodv.csv
```

#### Sample Analysis Output:
```text
============================================================
  MANET Routing Comparison: Baseline AODV vs AI-AODV
============================================================
  Baseline CSV : baseline-aodv.csv
  AI CSV       : ai-aodv.csv
------------------------------------------------------------
  Metric                        Baseline AODV        AI-AODV
------------------------------------------------------------
  Packet Delivery Ratio                 0.812          0.894 (*)
  Avg E2E Delay                  N/A (no tag)       14.25 ms
  Network Lifespan (s)                  200.0          200.0
  Total Energy Spent            N/A (no model)        48.32 J
------------------------------------------------------------

  PDR comparison (higher = better):
    Baseline: [#######################       ] 0.812
    AI-AODV:  [##########################    ] 0.894

  Lifespan comparison (higher = better):
    Baseline: [##############################] 200s
    AI-AODV:  [##############################] 200s

  AI-AODV PDR improvement: +10.1% (*)
============================================================
```

---

### Step 5: One-Shot Automated Test Execution

You can run steps 1 through 4 automatically with a single command using `run-experiment.sh`:

```bash
bash scratch/run-experiment.sh --seed 42 --simTime 200 --w1 0.4 --w2 0.4 --w3 0.2 --timeout 1.5
```

This script will:
1. Build both binaries automatically.
2. Execute baseline AODV and output `baseline-aodv-seed42.csv`.
3. Execute AI-AODV and output `ai-aodv-seed42.csv`.
4. Launch `analyze-results.py` and print the summary report.

---

### Step 6: Multi-Seed Statistical Validation

To verify results across multiple random topology/traffic seeds, execute a bash loop:

```bash
for seed in 1 2 3 4 5; do
  echo "--- Running Seed $seed ---"
  ./ns3 run "compare --protocol=2 --seed=$seed --CSVfileName=baseline-seed${seed}.csv"
  ./ns3 run "ai-routing --seed=$seed --CSVfileName=ai-seed${seed}.csv"
  python3 scratch/analyze-results.py "baseline-seed${seed}.csv" "ai-seed${seed}.csv"
done
```

---

## 5. CSV Output Schema Reference

### Baseline Output (`baseline-aodv.csv`)
| Column | Description |
|---|---|
| `SimulationSecond` | Elapsed simulation time in seconds (0 to simTime) |
| `ReceiveRate` | Current receive throughput in kbps |
| `PacketsReceived` | Number of packets received in the current second |
| `NumberOfSinks` | Active destination sink nodes (default: 10) |
| `RoutingProtocol` | Protocol code (2 = AODV) |
| `TransmissionPower` | Radio transmission power in dBm (default: 7.5 dBm) |

### AI Output (`ai-aodv.csv`)
| Column | Description |
|---|---|
| `Second` | Elapsed simulation time in seconds |
| `RxRate_kbps` | Current throughput in kbps |
| `PktsRcvd` | Packets received in current second |
| `PktsSent` | Total estimated packets transmitted |
| `AvgDelay_ms` | Mean End-to-End delay (ms) measured via `TimestampTag` |
| `MinResidualFrac` | Remaining energy fraction of the most depleted node (0.0 to 1.0) |
| `TotalEnergySpentJ` | Cumulative energy consumed across all nodes (Joules) |
| `Protocol` | Protocol identifier (`AI-AODV`) |

---

## 6. Troubleshooting & FAQs

### Q1: `Command not found: ./ns3`
**Solution**: Ensure you are in the `ns-3.48/ns-3.48` directory where the `./ns3` executable script resides.

### Q2: `FileNotFoundError: manet100.csv`
**Solution**: Verify `manet100.csv` exists in `scratch/`. The simulator loads topology coordinates from `scratch/manet100.csv`.

### Q3: How do I change the weight parameters to favor energy over delay?
**Solution**: Adjust `--w1`, `--w2`, and `--w3` when launching `ai-routing`. The weights must sum to 1.0 (e.g., `--w1=0.2 --w2=0.7 --w3=0.1`).

### Q4: Why is AvgDelay N/A in the baseline CSV?
**Solution**: The baseline `compare.cc` script does not inject timestamp tags into packets. The custom `TimestampTag` is unique to `ai-routing.cc`.

---

*Guide generated for NS-3.48 AI MANET Optimization System.*
