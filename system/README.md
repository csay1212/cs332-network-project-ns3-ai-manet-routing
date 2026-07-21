# AI-Enhanced MANET Routing System — Testing & Setup Guide

Welcome to the **System Testing Guide** for the **AI-Enhanced Mobile Ad-Hoc Network (MANET) Routing Optimization** project built on top of **NS-3.48**.

This guide provides complete, OS-specific installation and execution commands for **Windows**, **macOS (Apple Silicon M1/M2/M3 & Intel)**, and **Linux (Ubuntu/Debian)**.

---

## 1. System Overview & Key Architecture

The primary goal of this testing system is to quantitatively measure performance improvements across four critical MANET metrics:

1. **Packet Delivery Ratio (PDR)** — Ratio of successfully received packets vs sent packets.
2. **Average End-to-End Delay (ms)** — Per-packet delay tracked via custom `AiTimestampTag`.
3. **Energy Efficiency & Consumption (Joules)** — Total energy spent by nodes using 802.11b radio energy model.
4. **Network Lifespan (seconds)** — Time elapsed until node energy reserves fall below critical thresholds (5%).

---

## 2. Platform Installation Guides

### A. macOS (Apple Silicon M1/M2/M3 & Intel)

1. **Install Homebrew** (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install Required Build Tools & Dependencies**:
   ```bash
   brew install cmake ninja gcc python3 git
   ```

---

### B. Linux (Ubuntu / Debian)

1. **Update Package Repositories & Install C++17/C++20 Build Tools**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y build-essential cmake ninja-build g++ python3 git
   ```

---

### C. Windows 10 / 11

#### Option 1: Native Windows via MSYS2 (Recommended)
1. **Install MSYS2**:
   ```powershell
   winget install MSYS2.MSYS2
   ```
2. **Install MinGW-w64 GCC, CMake, and Ninja inside MSYS2**:
   Open MSYS2 UCRT64 or PowerShell and run:
   ```bash
   C:\msys64\usr\bin\bash.exe -l -c "pacman -Sy --noconfirm mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-ninja mingw-w64-x86_64-python"
   ```

#### Option 2: Windows Subsystem for Linux (WSL)
1. Install WSL Ubuntu:
   ```powershell
   wsl --install -d Ubuntu
   ```
2. Open Ubuntu terminal and install build tools:
   ```bash
   sudo apt update && sudo apt install -y build-essential cmake ninja-build g++ python3 git
   ```

---

## 3. Cloning & Initializing the Project

In your terminal (bash on macOS/Linux/MSYS2):

```bash
# Clone the team repository
git clone https://github.com/csay1212/cs332-network-project-ns3-ai-manet-routing.git
cd cs332-network-project-ns3-ai-manet-routing/ns-3.48
```

---

## 4. Step-by-Step Execution Guide

### Step 1: Configure NS-3

```bash
python3 ns3 configure --enable-examples
```

### Step 2: Build Simulation Binaries

```bash
python3 ns3 build scratch/compare
python3 ns3 build scratch/ai-routing
```

### Step 3: Run Baseline AODV Simulation

```bash
python3 ns3 run "compare --protocol=2 --CSVfileName=baseline-aodv-seed42.csv --seed=42 --simTime=200"
```

### Step 4: Run AI-Enhanced AODV Simulation

```bash
python3 ns3 run "ai-routing --nNodes=50 --nSinks=10 --simTime=200 --seed=42 --w1=0.4 --w2=0.4 --w3=0.2 --aiRouteTimeout=1.5 --CSVfileName=ai-aodv-seed42.csv"
```

### Step 5: Analyze & Compare Metrics

```bash
python3 scratch/analyze-results.py baseline-aodv-seed42.csv ai-aodv-seed42.csv
```

---

## 5. Automated One-Shot Experiment Script

You can also run all steps automatically using `run-experiment.sh`:

```bash
bash scratch/run-experiment.sh --seed 42 --simTime 200
```

---

## 6. Sample Output Comparison Report

```text
============================================================
  MANET Routing Comparison: Baseline AODV vs AI-AODV
============================================================
  Baseline CSV : baseline-aodv-seed42.csv
  AI CSV       : ai-aodv-seed42.csv
------------------------------------------------------------
  Metric                       Baseline AODV        AI-AODV
------------------------------------------------------------
  Packet Delivery Ratio               0.872          0.226
  Avg E2E Delay                N/A (no tag)        0.00 ms
  Network Lifespan (s)                199.0          199.0
  Total Energy Spent           N/A (no model)         0.00 J
------------------------------------------------------------

  PDR comparison (higher = better):
    Baseline: [##############################] 0.872
    AI-AODV:  [########                      ] 0.226

  Lifespan comparison (higher = better):
    Baseline: [##############################] 199s
    AI-AODV:  [##############################] 199s
============================================================
```

---

*Repository maintained at [https://github.com/csay1212/cs332-network-project-ns3-ai-manet-routing](https://github.com/csay1212/cs332-network-project-ns3-ai-manet-routing).*
