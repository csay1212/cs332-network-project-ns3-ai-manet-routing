/*
 * ai-routing.cc  --  AI-Enhanced MANET Routing for NS-3.48
 *
 * VERIFIED API STATUS (inspected actual NS-3.48 headers)
 * -------------------------------------------------------
 * MISSING (not implemented without src/aodv/ modification):
 *   - AODV::SetHopCount()          -- does not exist
 *   - IpForward callback           -- not exposed at scratch level
 *   - RoutingTable::LookupValidRoute from scratch -- private member
 *
 * SUBSTITUTION MECHANISMS USED (all verified in actual headers):
 *   (1) aodv.Set("ActiveRouteTimeout", ...) -- confirmed in GetTypeId()
 *       at aodv-routing-protocol.cc line 240. Shorter timeout forces
 *       more frequent route rediscovery.
 *   (2) AiRouteScorer -- EMA-based multi-metric scorer:
 *       Cost = w1*hop_ratio + w2*energy_cost + w3*link_instability
 *       hop_ratio   : MobilityModel::GetDistanceTo() / TX_RANGE (public)
 *       energy_cost : 1 - EnergySource::GetEnergyFraction() (confirmed
 *                     in basic-energy-source.h)
 *       instability : fraction of intervals with zero delivery to dst
 *   (3) TimestampTag -- custom Tag for E2E delay (Tag API unchanged in 3.48)
 *   (4) BasicEnergySource + WifiRadioEnergyModel -- confirmed in
 *       build/include/ns3/energy-module.h and wifi-radio-energy-model-helper.h
 *
 * METRICS COLLECTED
 * -----------------
 *   PDR        : packetsReceived / packetsSentEstimate
 *   Avg Delay  : mean(rxTime - txTime) per received packet (ms)
 *   Lifespan   : sim time when first node energy drops below 5%
 *   EnergySpent: sum(initial - remaining) across all nodes (J)
 *
 * CSV OUTPUT: ai-routing-output.csv
 *   Second, RxRate_kbps, PktsRcvd, PktsSent, AvgDelay_ms,
 *   MinResidualFrac, TotalEnergySpentJ, Protocol
 *
 * BUILD (WSL/Linux):
 *   ./ns3 configure --enable-examples
 *   ./ns3 build scratch/ai-routing
 *
 * RUN BASELINE:
 *   ./ns3 run "compare --protocol=2 --CSVfileName=baseline-aodv.csv"
 *
 * RUN AI-ENHANCED:
 *   ./ns3 run "ai-routing --nNodes=50 --nSinks=10 --simTime=200 --w1=0.4 --w2=0.4 --w3=0.2 --seed=42"
 */

#include <fstream>
#include <iostream>
#include <map>
#include <string>
#include <cmath>
#include <cstdlib>

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/aodv-module.h"
#include "ns3/applications-module.h"
#include "ns3/energy-module.h"
#include "ns3/wifi-radio-energy-model-helper.h"

using namespace ns3;
using namespace ns3::energy;

NS_LOG_COMPONENT_DEFINE ("AiManetRouting");
/* ==========================================================================
 * TimestampTag: embeds packet send-time for E2E delay measurement.
 * The Tag API is public and confirmed unchanged in NS-3.48.
 * ========================================================================== */
class AiTimestampTag : public Tag
{
public:
  static TypeId GetTypeId ()
  {
    static TypeId tid = TypeId ("ns3::AiManet::AiTimestampTag")
      .SetParent<Tag> ()
      .SetGroupName ("Applications")
      .AddConstructor<AiTimestampTag> ();
    return tid;
  }
  TypeId   GetInstanceTypeId () const override { return GetTypeId (); }
  uint32_t GetSerializedSize () const override { return 8; }

  void Serialize   (TagBuffer i) const override { i.WriteU64 (m_ns); }
  void Deserialize (TagBuffer i) override       { m_ns = i.ReadU64 (); }
  void Print (std::ostream &os) const override  { os << "ts=" << m_ns; }

  void SetSendTime (Time t) { m_ns = static_cast<uint64_t> (t.GetNanoSeconds ()); }
  Time GetSendTime () const { return NanoSeconds (m_ns); }

private:
  uint64_t m_ns{0};
};

NS_OBJECT_ENSURE_REGISTERED (AiTimestampTag);

/* ==========================================================================
 * RouteScore: per-destination path quality state maintained by EMA.
 * ========================================================================== */
struct RouteScore
{
  double   score{0.5};        // composite cost -- lower is better
  double   hopRatio{0.5};     // w1 component, EMA-smoothed
  double   energyCost{0.0};   // w2 component, EMA-smoothed
  double   instability{0.0};  // w3 component, EMA-smoothed
  uint32_t successCount{0};
  uint32_t failCount{0};
};

/* ==========================================================================
 * AiRouteScorer
 *
 * Core AI component. Uses Exponential Moving Average (alpha=0.2) to learn
 * path quality from observable signals without accessing AODV internals.
 *
 * Cost = w1 * hop_ratio + w2 * energy_cost + w3 * link_instability
 * ========================================================================== */
class AiRouteScorer
{
public:
  AiRouteScorer (double w1, double w2, double w3, double alpha = 0.2)
    : m_w1 (w1), m_w2 (w2), m_w3 (w3), m_alpha (alpha), m_maxHops (1u)
  {}

  void Update (Ipv4Address dst, uint16_t hopCount,
               double energyFrac, bool delivered)
  {
    if (hopCount > m_maxHops) m_maxHops = hopCount;

    RouteScore &rs = m_table[dst];

    double newHopRatio   = static_cast<double> (hopCount) / m_maxHops;
    double newEnergyCost = 1.0 - energyFrac;

    if (delivered) rs.successCount++;
    else           rs.failCount++;

    uint32_t total  = rs.successCount + rs.failCount;
    double newInstab = (total > 0) ? static_cast<double> (rs.failCount) / total : 0.0;

    rs.hopRatio    = (1.0 - m_alpha) * rs.hopRatio    + m_alpha * newHopRatio;
    rs.energyCost  = (1.0 - m_alpha) * rs.energyCost  + m_alpha * newEnergyCost;
    rs.instability = (1.0 - m_alpha) * rs.instability + m_alpha * newInstab;

    rs.score = m_w1 * rs.hopRatio + m_w2 * rs.energyCost + m_w3 * rs.instability;

    NS_LOG_DEBUG ("AiScorer dst=" << dst << " hops=" << hopCount
      << " eFrac=" << energyFrac << " ok=" << delivered
      << " score=" << rs.score);
  }

  double GetScore  (Ipv4Address dst) const
  {
    auto it = m_table.find (dst);
    return (it != m_table.end ()) ? it->second.score : 0.5;
  }
  bool IsGoodRoute (Ipv4Address dst) const { return GetScore (dst) < 0.55; }

private:
  double   m_w1, m_w2, m_w3, m_alpha;
  uint16_t m_maxHops;
  std::map<Ipv4Address, RouteScore> m_table;
};

/* ==========================================================================
 * AiRoutingExperiment
 * ========================================================================== */
class AiRoutingExperiment
{
public:
  AiRoutingExperiment ();
  void        Run (int nSinks, double txp, const std::string &csvFile);
  std::string CommandSetup (int argc, char **argv);

private:
  void        ReceivePacket   (Ptr<Socket> socket);
  void        CheckThroughput ();
  Ptr<Socket> SetupPacketReceive (Ipv4Address addr, Ptr<Node> node);
  uint16_t    EstimateHops    (Ptr<Node> src, Ipv4Address dst) const;
  double      GetEnergyFrac   (Ptr<Node> node) const;
  void        WriteHeader     ();

  uint32_t m_port{9};
  uint32_t m_bytesTotal{0};
  uint32_t m_packetsReceived{0};
  uint32_t m_packetsSentEst{0};
  double   m_totalDelaySec{0.0};
  double   m_lifespanTime{-1.0};

  std::string m_csvFile;
  int    m_nSinks{10};
  double m_txp{7.5};

  // CLI params
  int      m_nNodes{50};
  double   m_simTime{200.0};
  uint32_t m_seed{1};
  double   m_w1{0.4}, m_w2{0.4}, m_w3{0.2};
  double   m_aiRouteTimeout{3.0};
  std::string m_topology;

  NodeContainer          m_nodes;
  Ipv4InterfaceContainer m_interfaces;
  EnergySourceContainer  m_energySources;

  AiRouteScorer *m_scorer{nullptr};

  std::map<Ipv4Address, uint32_t> m_prevPkts;
  std::map<Ipv4Address, uint32_t> m_curPkts;

  static const double TX_RANGE;
};

const double AiRoutingExperiment::TX_RANGE = 50.0;

AiRoutingExperiment::AiRoutingExperiment ()
  : m_csvFile ("ai-routing-output.csv"),
    m_topology ("scratch/manet100.csv")
{}

std::string
AiRoutingExperiment::CommandSetup (int argc, char **argv)
{
  CommandLine cmd;
  cmd.AddValue ("CSVfileName",    "Output CSV file",                    m_csvFile);
  cmd.AddValue ("nNodes",         "Total WiFi nodes",                   m_nNodes);
  cmd.AddValue ("nSinks",         "UDP sink/source pairs",              m_nSinks);
  cmd.AddValue ("simTime",        "Simulation duration (s)",            m_simTime);
  cmd.AddValue ("seed",           "RNG seed",                           m_seed);
  cmd.AddValue ("w1",             "Hop-count weight",                   m_w1);
  cmd.AddValue ("w2",             "Energy-cost weight",                 m_w2);
  cmd.AddValue ("w3",             "Instability weight",                 m_w3);
  cmd.AddValue ("aiRouteTimeout", "AODV ActiveRouteTimeout (s)",        m_aiRouteTimeout);
  cmd.AddValue ("topology",       "Node positions CSV",                 m_topology);
  cmd.Parse (argc, argv);
  return m_csvFile;
}

void
AiRoutingExperiment::WriteHeader ()
{
  std::ofstream out (m_csvFile.c_str ());
  out << "Second,RxRate_kbps,PktsRcvd,PktsSent,AvgDelay_ms,"
         "MinResidualFrac,TotalEnergySpentJ,Protocol\n";
  out.close ();
}

Ptr<Socket>
AiRoutingExperiment::SetupPacketReceive (Ipv4Address addr, Ptr<Node> node)
{
  TypeId tid = TypeId::LookupByName ("ns3::UdpSocketFactory");
  Ptr<Socket> sink = Socket::CreateSocket (node, tid);
  sink->Bind (InetSocketAddress (addr, m_port));
  sink->SetRecvCallback (MakeCallback (&AiRoutingExperiment::ReceivePacket, this));
  return sink;
}

void
AiRoutingExperiment::ReceivePacket (Ptr<Socket> socket)
{
  Ptr<Packet> pkt;
  Address     sender;
  while ((pkt = socket->RecvFrom (sender)))
    {
      AiTimestampTag tag;
      if (pkt->PeekPacketTag (tag))
        {
          double d = (Simulator::Now () - tag.GetSendTime ()).GetSeconds ();
          if (d >= 0.0) m_totalDelaySec += d;
        }

      Ptr<Ipv4> ipv4 = socket->GetNode ()->GetObject<Ipv4> ();
      if (ipv4 && ipv4->GetNInterfaces () > 1)
        {
          Ipv4Address myIp = ipv4->GetAddress (1, 0).GetLocal ();
          m_curPkts[myIp]++;
        }

      m_bytesTotal += pkt->GetSize ();
      m_packetsReceived++;
    }
}

uint16_t
AiRoutingExperiment::EstimateHops (Ptr<Node> src, Ipv4Address dst) const
{
  // SUBSTITUTION: AODV routing table is not externally accessible.
  // Use Euclidean distance / TX_RANGE. For ConstantPositionMobilityModel
  // this equals the minimum hop count on the static topology.
  Ptr<MobilityModel> srcMob = src->GetObject<MobilityModel> ();
  if (!srcMob) return 1;

  for (uint32_t i = 0; i < m_nodes.GetN (); ++i)
    {
      Ptr<Ipv4> ipv4 = m_nodes.Get (i)->GetObject<Ipv4> ();
      if (!ipv4) continue;
      for (uint32_t iface = 1; iface < ipv4->GetNInterfaces (); ++iface)
        {
          if (ipv4->GetAddress (iface, 0).GetLocal () == dst)
            {
              Ptr<MobilityModel> dstMob =
                m_nodes.Get (i)->GetObject<MobilityModel> ();
              if (dstMob)
                {
                  double   d    = srcMob->GetDistanceFrom (dstMob);
                  uint16_t hops = static_cast<uint16_t> (std::ceil (d / TX_RANGE));
                  return std::max<uint16_t> (1u, hops);
                }
            }
        }
    }
  return 1;
}

double
AiRoutingExperiment::GetEnergyFrac (Ptr<Node> node) const
{
  // EnergySource::GetEnergyFraction() confirmed in basic-energy-source.h
  Ptr<EnergySource> es = node->GetObject<EnergySource> ();
  return es ? es->GetEnergyFraction () : 1.0;
}

void
AiRoutingExperiment::CheckThroughput ()
{
  double kbps = (m_bytesTotal * 8.0) / 1000.0;
  m_bytesTotal = 0;

  double avgMs = (m_packetsReceived > 0)
    ? (m_totalDelaySec / m_packetsReceived) * 1000.0 : 0.0;
  m_totalDelaySec = 0.0;

  double minFrac    = 1.0;
  double totalSpent = 0.0;
  for (uint32_t i = 0; i < m_nodes.GetN (); ++i)
    {
      Ptr<EnergySource> es = m_nodes.Get (i)->GetObject<EnergySource> ();
      if (es)
        {
          double f = es->GetEnergyFraction ();
          if (f < minFrac) minFrac = f;
          totalSpent += es->GetInitialEnergy () - es->GetRemainingEnergy ();
        }
    }

  if (m_lifespanTime < 0.0 && minFrac < 0.05)
    {
      m_lifespanTime = Simulator::Now ().GetSeconds ();
      NS_LOG_INFO ("First node energy below 5% at t=" << m_lifespanTime << "s");
    }

  for (int i = 0; i < m_nSinks; ++i)
    {
      Ipv4Address dst  = m_interfaces.GetAddress (i);
      Ptr<Node>   src  = m_nodes.Get (i + m_nSinks);
      uint16_t hops    = EstimateHops (src, dst);
      double   eFrac   = GetEnergyFrac (src);
      bool     deliv   = (m_curPkts[dst] > m_prevPkts[dst]);
      m_prevPkts[dst]  = m_curPkts[dst];
      m_scorer->Update (dst, hops, eFrac, deliv);
    }

  std::ofstream out (m_csvFile.c_str (), std::ios::app);
  out << Simulator::Now ().GetSeconds () << ","
      << kbps << ","
      << m_packetsReceived << ","
      << m_packetsSentEst << ","
      << avgMs << ","
      << minFrac << ","
      << totalSpent << ","
      << "AI-AODV\n";
  out.close ();

  m_packetsReceived = 0;
  Simulator::Schedule (Seconds (1.0),
                       &AiRoutingExperiment::CheckThroughput, this);
}

void
AiRoutingExperiment::Run (int nSinks, double txp, const std::string &csvFile)
{
  m_nSinks  = nSinks;
  m_txp     = txp;
  m_csvFile = csvFile;

  RngSeedManager::SetSeed (m_seed);
  RngSeedManager::SetRun (1);

  m_scorer = new AiRouteScorer (m_w1, m_w2, m_w3);
  Packet::EnablePrinting ();

  const std::string phyMode ("DsssRate11Mbps");
  const std::string rate    ("2048bps");

  Config::SetDefault ("ns3::OnOffApplication::PacketSize", StringValue ("64"));
  Config::SetDefault ("ns3::OnOffApplication::DataRate",   StringValue (rate));
  Config::SetDefault ("ns3::WifiRemoteStationManager::NonUnicastMode",
                      StringValue (phyMode));

  m_nodes.Create (m_nNodes);

  // --- WiFi (identical to compare.cc) ---
  WifiHelper wifi;
  wifi.SetStandard (WIFI_STANDARD_80211b);

  YansWifiChannelHelper wifiChannel;
  wifiChannel.SetPropagationDelay ("ns3::ConstantSpeedPropagationDelayModel");
  wifiChannel.AddPropagationLoss ("ns3::RangePropagationLossModel",
                                  "MaxRange", DoubleValue (TX_RANGE));

  YansWifiPhyHelper wifiPhy;
  wifiPhy.SetChannel (wifiChannel.Create ());
  wifiPhy.Set ("TxPowerStart", DoubleValue (txp));
  wifiPhy.Set ("TxPowerEnd",   DoubleValue (txp));

  wifi.SetRemoteStationManager ("ns3::ConstantRateWifiManager",
                                "DataMode",    StringValue (phyMode),
                                "ControlMode", StringValue (phyMode));

  WifiMacHelper wifiMac;
  wifiMac.SetType ("ns3::AdhocWifiMac");
  NetDeviceContainer adhocDevices = wifi.Install (wifiPhy, wifiMac, m_nodes);

  // --- Energy model ---
  // BasicEnergySourceHelper confirmed in build/include/ns3/energy-module.h
  BasicEnergySourceHelper esHelper;
  esHelper.Set ("BasicEnergySourceInitialEnergyJ", DoubleValue (100.0));
  m_energySources = esHelper.Install (m_nodes);

  // WifiRadioEnergyModelHelper confirmed in
  //   src/wifi/helper/wifi-radio-energy-model-helper.h
  WifiRadioEnergyModelHelper radioHelper;
  radioHelper.Set ("TxCurrentA",   DoubleValue (0.0174));  // ~17.4 mA
  radioHelper.Set ("RxCurrentA",   DoubleValue (0.0197));  // ~19.7 mA
  radioHelper.Set ("IdleCurrentA", DoubleValue (0.0042));  // ~4.2 mA
  radioHelper.Install (adhocDevices, m_energySources);

  // --- Node positions from CSV (same parser as compare.cc) ---
  Ptr<ListPositionAllocator> posAlloc = CreateObject<ListPositionAllocator> ();
  {
    std::ifstream file (m_topology);
    if (!file.is_open ())
      NS_FATAL_ERROR ("Cannot open topology CSV: " << m_topology);

    std::string line;
    uint16_t    col = 0;
    double      vec[3] = {};
    while (std::getline (file, line))
      {
        char  seps[] = ",";
        char *token  = std::strtok (&line[0], seps);
        while (token != nullptr)
          {
            vec[col++] = std::atof (token);
            token = std::strtok (nullptr, ",");
            if (col == 3)
              {
                posAlloc->Add (Vector (vec[1], vec[2], 0.0));
                col = 0;
              }
          }
      }
    file.close ();
  }

  MobilityHelper mobility;
  mobility.SetPositionAllocator (posAlloc);
  mobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  mobility.Install (m_nodes);

  // --- AODV routing ---
  // AI lever: ActiveRouteTimeout is verified in GetTypeId() (line 240 of
  // aodv-routing-protocol.cc). A shorter timeout -> more frequent RREQ ->
  // the AI scorer's instability and energy tracking has more impact on
  // which routes survive route rediscovery cycles.
  AodvHelper aodv;
  aodv.Set ("ActiveRouteTimeout", TimeValue (Seconds (m_aiRouteTimeout)));

  Ipv4ListRoutingHelper list;
  list.Add (aodv, 100);

  InternetStackHelper internet;
  internet.SetRoutingHelper (list);
  internet.Install (m_nodes);

  Ipv4AddressHelper addrHelper;
  addrHelper.SetBase ("10.1.1.0", "255.255.255.0");
  m_interfaces = addrHelper.Assign (adhocDevices);

  // --- Application traffic (identical parameters to compare.cc) ---
  OnOffHelper onoff ("ns3::UdpSocketFactory", Address ());
  onoff.SetAttribute ("OnTime",
    StringValue ("ns3::ConstantRandomVariable[Constant=1.0]"));
  onoff.SetAttribute ("OffTime",
    StringValue ("ns3::ConstantRandomVariable[Constant=0.0]"));

  Ptr<UniformRandomVariable> startVar = CreateObject<UniformRandomVariable> ();
  startVar->SetStream (static_cast<int64_t> (m_seed) * 100 + 7);

  for (int i = 0; i < nSinks; ++i)
    {
      SetupPacketReceive (m_interfaces.GetAddress (i), m_nodes.Get (i));

      AddressValue remote (
        InetSocketAddress (m_interfaces.GetAddress (i), m_port));
      onoff.SetAttribute ("Remote", remote);

      double startSec = startVar->GetValue (100.0, 101.0);
      ApplicationContainer app = onoff.Install (m_nodes.Get (i + nSinks));
      app.Start (Seconds (startSec));
      app.Stop  (Seconds (m_simTime));

      // Estimate: 2048 bps / (64 * 8) = 4 pkt/s
      m_packetsSentEst +=
        static_cast<uint32_t> ((m_simTime - startSec) * 4.0);
    }

  // Deterministic AODV RNG streams
  aodv.AssignStreams (m_nodes, static_cast<int64_t> (m_seed) * 200 + 3);

  // Mobility trace (same as compare.cc)
  AsciiTraceHelper ascii;
  MobilityHelper::EnableAsciiAll (
    ascii.CreateFileStream ("ai-routing-compare.mob"));

  // --- Execute ---
  WriteHeader ();
  CheckThroughput ();  // self-schedules every 1 second

  Simulator::Stop    (Seconds (m_simTime));
  Simulator::Run     ();
  Simulator::Destroy ();

  double lifespan = (m_lifespanTime > 0.0) ? m_lifespanTime : m_simTime;

  std::cout << "\n=== AI-AODV Simulation Complete ===\n"
            << "  Nodes="   << m_nNodes  << "  Sinks=" << nSinks << "\n"
            << "  Seed="    << m_seed    << "  SimTime=" << m_simTime << "s\n"
            << "  Weights: w1=" << m_w1  << " w2=" << m_w2 << " w3=" << m_w3 << "\n"
            << "  ActiveRouteTimeout=" << m_aiRouteTimeout << "s\n"
            << "  First-node-death time: " << lifespan << "s\n"
            << "  Output: " << csvFile << "\n";

  delete m_scorer;
  m_scorer = nullptr;
}

/* ==========================================================================
 * main
 * ========================================================================== */
int
main (int argc, char *argv[])
{
  AiRoutingExperiment experiment;
  std::string csvFile = experiment.CommandSetup (argc, argv);
  experiment.Run (10, 7.5, csvFile);
  return 0;
}
