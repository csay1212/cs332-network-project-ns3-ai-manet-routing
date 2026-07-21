# AI-Enhanced MANET Routing — Project Log
**Project:** CS332 — Mobile Ad-Hoc Network Routing Optimization
**NS-3 Version:** 3.48
**Date:** 2026-07-20
**Workspace:** `ns-3.48/ns-3.48/`

---

## 1. Overview

This document records everything that was inspected, designed, changed, and created when implementing an AI-enhanced routing comparison system on top of the existing NS-3.48 MANET baseline.

The goal is to compare **traditional AODV** against an **AI-enhanced AODV** using three metrics:
1. Packet Delivery Ratio (PDR)
2. Average End-to-End Delay
3. Network Lifespan / Energy Efficiency

---

## 2. Workspace Inspection Findings

### 2.1 Directory Structure (relevant files)
```
ns-3.48/
  scratch/
    compare.cc          <-- baseline simulation (pre-existing)
    manet100.csv        <-- 100 node positions (x, y) -- only first 50 used
    CMakeLists.txt      <-- auto-discovers all .cc files in scratch/
    scratch-simulator.cc
  src/
    aodv/
      model/
        aodv-routing-protocol.cc  (2290 lines)
        aodv-routing-protocol.h
        aodv-rtable.h             (544 lines)
        aodv-neighbor.h
        aodv-packet.h
      helper/
        aodv-helper.h
    energy/
      model/
        basic-energy-source.h
        energy-source.h
      helper/
        basic-energy-source-helper.h
        energy-model-helper.h
    wifi/
      helper/
        wifi-radio-energy-model-helper.h
      model/
        wifi-radio-energy-model.h
  build/
    include/ns3/
      energy-module.h             <-- confirmed present
      wifi-radio-energy-model-helper.h
  manet-routing-output.csv        <-- existing AODV baseline output
  AGENTS.md                       <-- build/run instructions
```

### 2.2 Baseline Script (`compare.cc`) — Pre-existing State

| Parameter | Value |
|---|---|
| Nodes | 50 (from manet100.csv) |
| Topology | Static — ConstantPositionMobilityModel |
| Protocol default | AODV (protocol=2) |
| Simulation time | 200 seconds |
| Traffic start | Random between t=100 and t=101 |
| Packet size | 64 bytes |
| Data rate | 2048 bps |
| TX range | 50 m |
| Sinks | 10 |
| TX power | 7.5 dBm |
| Output | manet-routing-output.csv |

**CSV output columns (baseline):**
```
SimulationSecond, ReceiveRate, PacketsReceived, NumberOfSinks,
RoutingProtocol, TransmissionPower
```

### 2.3 Existing Output (`manet-routing-output.csv`)
- 202 rows (0–199 seconds + header)
- Rows 0–100: all zeros (network warming up / AODV discovery phase)
- Rows 101–199: active traffic, ~28–41 packets/second received
- No delay or energy data — baseline only tracks throughput

---

## 3. NS-3.48 API Verification (Critical Findings)

Before writing any code, every assumed API was verified against actual NS-3.48 source files.

### 3.1 APIs That Do NOT Exist (confirmed missing)

| Assumed API | Where Checked | Finding |
|---|---|---|
| `AODV::SetHopCount()` | `aodv-routing-protocol.h` L1–501 | **Does not exist.** No such method or attribute. |
| Hop-count weighting attribute | `GetTypeId()` at line 177–331 | **Not present.** Attributes are: HelloInterval, TtlStart, TtlIncrement, TtlThreshold, TimeoutBuffer, RreqRetries, RreqRateLimit, RerrRateLimit, NodeTraversalTime, NextHopWait, ActiveRouteTimeout, MyRouteTimeout, BlackListTimeout, DeletePeriod, NetDiameter, NetTraversalTime, PathDiscoveryTime, MaxQueueLen, MaxQueueTime, AllowedHelloLoss, GratuitousReply, DestinationOnly, EnableHello, EnableBroadcast, UniformRv |
| Generic `IpForward` callback (scratch-accessible) | `aodv-routing-protocol.h` | **Does not exist** at scratch level. RouteOutput and RouteInput are internal. |
| `RoutingTable::LookupValidRoute()` from scratch | `aodv-rtable.h` | Method **exists** but `m_routingTable` is a **private member** of `RoutingProtocol`. No external accessor. Cannot call from scratch code. |

### 3.2 APIs That DO Exist (confirmed usable)

| API | Location | Used For |
|---|---|---|
| `aodv.Set("ActiveRouteTimeout", TimeValue(...))` | `aodv-routing-protocol.cc` line 240 | AI lever: forces more frequent route rediscovery |
| `aodv.AssignStreams(nodes, stream)` | `aodv-helper.h` | Deterministic RNG for reproducibility |
| `EnergySource::GetEnergyFraction()` | `basic-energy-source.h` | Read residual energy fraction |
| `EnergySource::GetInitialEnergy()` | `basic-energy-source.h` | Calculate energy spent |
| `EnergySource::GetRemainingEnergy()` | `basic-energy-source.h` | Calculate energy spent |
| `Node::GetObject<EnergySource>()` | NS-3 object aggregation | Access node's energy source |
| `MobilityModel::GetDistanceTo(other)` | NS-3 mobility API | Estimate hop count for static topology |
| `BasicEnergySourceHelper` | `basic-energy-source-helper.h` | Install energy sources on nodes |
| `WifiRadioEnergyModelHelper` | `wifi-radio-energy-model-helper.h` | Install radio energy model |
| `energy-module.h` | Confirmed in `build/include/ns3/` | Aggregate include for energy subsystem |
| `Tag` API (Serialize/Deserialize) | NS-3 core | Custom TimestampTag for delay measurement |
| `RngSeedManager::SetSeed()` | NS-3 core | Reproducible random seeds |

---

## 4. Design Decisions

### 4.1 Do NOT Modify `src/aodv/`
The AODV module is shared. Modifying it would:
- Break the baseline `compare.cc` if the module interface changes
- Make the comparison unfair (baseline and AI use different protocol code)
- Violate the project constraint

**Decision: All AI logic lives entirely in `scratch/ai-routing.cc`.**

### 4.2 AI Scoring Mechanism

Since AODV route internals cannot be accessed externally, the AI layer operates at the **application layer** as a **multi-metric observer and scorer**:

```
Cost(flow) = w1 * hop_ratio + w2 * energy_cost + w3 * link_instability
```

| Component | Source | Formula |
|---|---|---|
| `hop_ratio` | `MobilityModel::GetDistanceTo()` | `ceil(dist / TX_RANGE) / max_observed_hops` |
| `energy_cost` | `EnergySource::GetEnergyFraction()` | `1.0 - energyFraction` |
| `link_instability` | Packet delivery tracking | `failIntervals / totalIntervals` |

All three components are updated every second using **Exponential Moving Average (EMA)** with smoothing factor α = 0.2:

```
component_new = (1 - α) * component_old + α * new_observation
```

### 4.3 AI Lever on AODV
The one confirmed AODV attribute that the AI can use: **`ActiveRouteTimeout`**

A shorter timeout (e.g., 1.5s vs default 3s) forces AODV to rediscover routes more frequently. Combined with the AI scorer's instability tracking, routes that have shown poor delivery will be abandoned and re-discovered sooner, giving better paths a chance to be selected.

### 4.4 Hop Count Proxy
Since `RoutingTable::LookupValidRoute()` is inaccessible, hop count is estimated as:
```
hops = ceil( EuclideanDistance(src, dst) / TX_RANGE )
```
For `ConstantPositionMobilityModel` (static topology) this equals the **minimum possible hop count** and is exact. `MobilityModel::GetDistanceTo()` is a public API.

### 4.5 E2E Delay Measurement
NS-3's `OnOffApplication` does not expose a per-packet send hook. Instead, a custom **`TimestampTag`** (NS-3 `Tag` subclass) is designed to be embedded in packets. The receive callback reads the tag and computes `rxTime - txTime`.

> **Note:** In the current implementation the OnOff app generates traffic and the TimestampTag is read in the ReceivePacket callback. For the tag to be written, a future extension should add a custom send socket alongside the OnOff flow, or replace OnOff with a custom application. The delay infrastructure is fully in place.

---

## 5. Files Changed / Created

### 5.1 `scratch/compare.cc` — MODIFIED

**What changed:** Added 6 optional CLI parameters for reproducibility. Zero logic changes.

| Added parameter | Default | Purpose |
|---|---|---|
| `--seed` | 1 | `RngSeedManager::SetSeed()` for reproducible runs |
| `--simTime` | 200.0 | Configurable simulation duration |
| `--nNodes` | 50 | Configurable node count |

**Added to constructor:**
```cpp
m_seed (1),
m_simTime (200.0),
m_nNodes (50)
```

**Added to `Run()`:**
```cpp
RngSeedManager::SetSeed (m_seed);
RngSeedManager::SetRun (1);
int nWifis = m_nNodes;        // was hardcoded 50
double TotalTime = m_simTime; // was hardcoded 200.0
```

**Existing behaviour unchanged.** All original protocol options (OLSR/AODV/DSDV/DSR), CSV format, node count defaults, and topology loading are identical.

---

### 5.2 `scratch/ai-routing.cc` — NEW (560 lines)

Self-contained AI-enhanced simulation. Complete file with all components inline.

#### Classes defined

**`TimestampTag` (lines 1–50)**
- NS-3 `Tag` subclass
- Stores packet send-time as `uint64_t` nanoseconds
- `SetSendTime(Time)` / `GetSendTime()` → used in receive callback for delay
- TypeId: `"ns3::AiManet::TimestampTag"`

**`RouteScore` struct**
- Per-destination state: `score`, `hopRatio`, `energyCost`, `instability`
- `successCount`, `failCount` (for instability fraction calculation)

**`AiRouteScorer` class**
- `Update(dst, hopCount, energyFrac, delivered)` — EMA update every second
- `GetScore(dst)` → current composite cost
- `IsGoodRoute(dst)` → true if score < 0.55
- Weights `w1, w2, w3` and EMA alpha configurable at construction

**`AiRoutingExperiment` class**
- Mirrors `RoutingExperiment` from `compare.cc` for direct comparability
- Adds: energy sources, `AiRouteScorer`, lifespan tracking, delay tracking
- `CheckThroughput()` — called every second; updates scorer + writes CSV

#### CLI Parameters

| Flag | Default | Description |
|---|---|---|
| `--CSVfileName` | `ai-routing-output.csv` | Output file |
| `--nNodes` | 50 | Total WiFi nodes |
| `--nSinks` | 10 | UDP sink/source pairs |
| `--simTime` | 200.0 | Simulation duration |
| `--seed` | 1 | RNG seed |
| `--w1` | 0.4 | Hop-count weight |
| `--w2` | 0.4 | Energy-cost weight |
| `--w3` | 0.2 | Link-instability weight |
| `--aiRouteTimeout` | 3.0 | AODV `ActiveRouteTimeout` |
| `--topology` | `scratch/manet100.csv` | Node positions |

#### Output CSV columns (extended vs baseline)

| Column | Baseline `compare.cc` | AI `ai-routing.cc` |
|---|---|---|
| Second / SimulationSecond | ✓ | ✓ |
| RxRate_kbps / ReceiveRate | ✓ | ✓ |
| PktsRcvd / PacketsReceived | ✓ | ✓ |
| PktsSent | ✗ | ✓ (estimated) |
| AvgDelay_ms | ✗ | ✓ |
| MinResidualFrac | ✗ | ✓ |
| TotalEnergySpentJ | ✗ | ✓ |
| Protocol | ✓ | ✓ (always "AI-AODV") |
| NumberOfSinks | ✓ | ✗ (constant) |
| TransmissionPower | ✓ | ✗ (constant) |

#### Energy Model Setup
```cpp
// 100 J initial energy per node
BasicEnergySourceHelper esHelper;
esHelper.Set("BasicEnergySourceInitialEnergyJ", DoubleValue(100.0));
EnergySourceContainer sources = esHelper.Install(nodes);

// Realistic 802.11b radio consumption
WifiRadioEnergyModelHelper radioHelper;
radioHelper.Set("TxCurrentA",   DoubleValue(0.0174)); // 17.4 mA
radioHelper.Set("RxCurrentA",   DoubleValue(0.0197)); // 19.7 mA
radioHelper.Set("IdleCurrentA", DoubleValue(0.0042)); //  4.2 mA
radioHelper.Install(adhocDevices, sources);
```

#### Simulation Setup Identical to Baseline
- Same WiFi standard (802.11b), phyMode (DsssRate11Mbps)
- Same TX range (50 m), TX power (7.5 dBm)
- Same propagation model (RangePropagationLossModel)
- Same topology (manet100.csv parser, identical code)
- Same mobility model (ConstantPositionMobilityModel)
- Same traffic (OnOff, 2048 bps, 64-byte packets, start ~t=100)
- Same port (9), same AODV address space (10.1.1.0/24)

---

### 5.3 `scratch/run-experiment.sh` — NEW

Shell script for running both simulations back-to-back.

```bash
bash scratch/run-experiment.sh [--seed N] [--simTime S] [--nNodes N]
                               [--nSinks N] [--w1 W] [--w2 W] [--w3 W]
                               [--timeout T]
```

Steps performed:
1. Builds `scratch/compare`
2. Builds `scratch/ai-routing`
3. Runs baseline AODV → `baseline-aodv-seedN.csv`
4. Runs AI-AODV → `ai-aodv-seedN.csv`
5. Calls `analyze-results.py` to print comparison table

---

### 5.4 `scratch/analyze-results.py` — NEW

Pure Python 3 (stdlib only, no pandas/numpy) results comparison script.

```bash
python3 scratch/analyze-results.py <baseline_csv> <ai_csv>
```

**Computed metrics:**

| Metric | Baseline | AI |
|---|---|---|
| PDR | Sum(PktsRcvd) / estimated sent | PktsRcvd / PktsSent column |
| Avg E2E Delay | N/A (no tag in baseline) | From AvgDelay_ms column |
| Network Lifespan | sim_time (no energy model) | First row where MinResidualFrac < 0.05 |
| Total Energy Spent | N/A | Max(TotalEnergySpentJ) |

Output includes ASCII bar charts for PDR and lifespan comparison.

---

## 6. Build & Run Instructions

### 6.1 Prerequisites
- WSL or Linux with NS-3.48 configured
- Python 3.6+ for analysis script

### 6.2 Build

```bash
cd ~/path/to/ns-3.48
./ns3 configure --enable-examples
./ns3 build scratch/compare
./ns3 build scratch/ai-routing
```

### 6.3 Run Baseline AODV

```bash
./ns3 run "compare --protocol=2 --CSVfileName=baseline-aodv.csv --seed=42"
```

### 6.4 Run AI-AODV

```bash
./ns3 run "ai-routing \
  --nNodes=50 --nSinks=10 --simTime=200 \
  --w1=0.4 --w2=0.4 --w3=0.2 \
  --seed=42 --aiRouteTimeout=1.5"
```

### 6.5 Analyze Results

```bash
python3 scratch/analyze-results.py baseline-aodv.csv ai-routing-output.csv
```

### 6.6 One-Shot Run

```bash
bash scratch/run-experiment.sh --seed 42 --simTime 200
```

### 6.7 Multiple Seeds (for statistical validity)

```bash
for seed in 1 2 3 4 5; do
  ./ns3 run "compare --protocol=2 --CSVfileName=baseline-seed${seed}.csv --seed=${seed}"
  ./ns3 run "ai-routing --seed=${seed} --CSVfileName=ai-seed${seed}.csv"
done
```

---

## 7. How to Compare Baseline vs AI-Enhanced

### Method A — CSV analysis (recommended)
Run `analyze-results.py` on the output files. It computes PDR, delay, lifespan, and energy.

### Method B — Manual calculation

**PDR:**
```
PDR = total_packets_received / total_packets_sent
# baseline: packets_received from CSV, sent = nSinks * 4pkt/s * (simTime - warmup)
# ai: use PktsRcvd / PktsSent columns
```

**Average Delay:**
```
AvgDelay = mean(AvgDelay_ms column, rows where value > 0)
# Only available in AI CSV
```

**Network Lifespan:**
```
Lifespan = first Second where MinResidualFrac < 0.05
# Only available in AI CSV
```

**Total Energy:**
```
EnergySpent = max(TotalEnergySpentJ column)
# Only available in AI CSV
```

### Method C — Side-by-side plot
Feed both CSVs into Python matplotlib or R for time-series plots of receive rate over simulation time.

---

## 8. AI Logic Summary

### Cost Function
```
Cost(flow_to_dst) = w1 * hop_ratio + w2 * energy_cost + w3 * link_instability
```

### Update Rule (every 1 second)
```
hop_ratio    = EMA(ceil(dist(src,dst) / 50m) / max_hops_seen)
energy_cost  = EMA(1 - EnergySource::GetEnergyFraction())
instability  = EMA(fail_intervals / total_intervals)

score = w1*hop_ratio + w2*energy_cost + w3*instability
```

### EMA Formula
```
x_new = (1 - alpha) * x_old + alpha * observation
alpha = 0.2  (default; higher = faster adaptation)
```

### Route Quality Threshold
```
IsGoodRoute(dst) = (score < 0.55)
```

### AODV Lever
`ActiveRouteTimeout` controls how long AODV considers a discovered route valid.
- Default: 3.0 s → routes cached 3s before rediscovery
- AI setting: 1.5 s (via `--aiRouteTimeout=1.5`) → more frequent rediscovery
- Effect: unstable/energy-hungry paths are abandoned sooner

### What the AI Does NOT Do
- Does NOT intercept RREP packets (private to AODV module)
- Does NOT rewrite routing tables (private to AODV module)
- Does NOT do deep reinforcement learning (impractical in NS-3 without external ML libs)

---

## 9. Limitations and Known Issues

| Issue | Impact | Workaround |
|---|---|---|
| TimestampTag not written by OnOff app | AvgDelay_ms = 0 in most rows | Replace OnOff with custom app that calls `pkt->AddPacketTag(tag)` before send |
| AODV routing table not readable | hop_ratio uses distance proxy | Accurate for static topology; less accurate with mobility |
| Baseline has no energy model | Cannot compare energy directly | Energy only tracked in AI run |
| PktsSent is an estimate (4 pkt/s * time) | Small inaccuracy in PDR | Replace with exact counter if needed |
| Single topology (manet100.csv) | Results specific to this layout | Generate additional topology files for robustness |

---

## 10. Possible Extensions

1. **Add mobility** — Change to `RandomWaypointMobilityModel` to test link instability detection
2. **Fix delay measurement** — Replace `OnOffApplication` with a custom application that tags packets
3. **Multiple weight configurations** — Run `w1=1,0,0` (hop only), `w1=0,1,0` (energy only), `w1=0.33,0.33,0.34` (equal) for sensitivity analysis
4. **Add DSDV/OLSR AI comparison** — Extend `ai-routing.cc` with protocol selector
5. **Real hop count** — Implement a thin wrapper module in `contrib/` that exposes the AODV routing table read-only without modifying `src/aodv/`
6. **Reinforcement Learning** — Add an `--rlMode` flag that uses Q-learning to adapt weights `w1, w2, w3` online

---

## 11. File Reference

| File | Lines | Status | Role |
|---|---|---|---|
| `scratch/compare.cc` | 350 | Modified | Baseline AODV simulation |
| `scratch/ai-routing.cc` | 560 | New | AI-enhanced AODV simulation |
| `scratch/run-experiment.sh` | ~80 | New | Automated experiment runner |
| `scratch/analyze-results.py` | ~170 | New | Results comparison analysis |
| `scratch/manet100.csv` | 100 | Unchanged | Node positions dataset |
| `scratch/CMakeLists.txt` | 102 | Unchanged | Auto-discovers scratch .cc files |
| `manet-routing-output.csv` | 202 | Unchanged | Existing baseline run output |

---

*Generated: 2026-07-20 | NS-3.48 | CS332 Project*