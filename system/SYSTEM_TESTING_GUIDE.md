# Multi-Platform Quick Testing Cheatsheet

Quick command reference for running the **AI-Enhanced MANET Routing Experiment** on **macOS**, **Linux**, and **Windows**.

---

## 1. Prerequisites Setup

### 🍏 macOS (Apple Silicon / Intel)
```bash
brew install cmake ninja gcc python3 git
```

### 🐧 Linux (Ubuntu / Debian)
```bash
sudo apt update && sudo apt install -y build-essential cmake ninja-build g++ python3 git
```

### 🪟 Windows (MSYS2)
```powershell
winget install MSYS2.MSYS2
C:\msys64\usr\bin\bash.exe -l -c "pacman -Sy --noconfirm mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-ninja mingw-w64-x86_64-python"
```

---

## 2. One-Shot Test Command

```bash
git clone https://github.com/csay1212/cs332-network-project-ns3-ai-manet-routing.git
cd cs332-network-project-ns3-ai-manet-routing/ns-3.48

# Run automated build, execution, and analysis
bash scratch/run-experiment.sh --seed 42 --simTime 200
```

---

## 3. Step-by-Step Commands

```bash
# 1. Configure
python3 ns3 configure --enable-examples

# 2. Build
python3 ns3 build scratch/compare
python3 ns3 build scratch/ai-routing

# 3. Run Baseline
python3 ns3 run "compare --protocol=2 --CSVfileName=baseline-aodv-seed42.csv --seed=42 --simTime=200"

# 4. Run AI-AODV
python3 ns3 run "ai-routing --nNodes=50 --nSinks=10 --simTime=200 --seed=42 --w1=0.4 --w2=0.4 --w3=0.2 --aiRouteTimeout=1.5 --CSVfileName=ai-aodv-seed42.csv"

# 5. Analyze Results
python3 scratch/analyze-results.py baseline-aodv-seed42.csv ai-aodv-seed42.csv
```

---

For complete architecture details, see [system/README.md](file:///c:/Users/saych/uni/Year4/Semester%202/CS332/Project/ns-3.48/system/README.md).
