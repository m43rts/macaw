# Specification — Disposable Mesh Comms System

## 1. Concept

A dense field of low-cost, solar-powered radio nodes deployed across an area of operations. Nodes self-organise into a mesh. Operators tether to any node by USB-serial to send and receive messages; the operator emits no RF. The mass and uniformity of nodes mask which node is being used and from where — adversary DF reveals the mesh, not the user.

Built on `Meshtastic` (open-source LoRa mesh) and extended for defence use: frequency agility, constant-rate cover traffic, gateway-only encryption, attritable hardware.

## 2. Operational concept

| Aspect | Choice |
|---|---|
| Deployment | UAS airdrop and/or hand-thrown by infantry |
| Density | Sized so each node has ≥3 neighbours at ≥500 m link range; overprovision freely (nodes are cheap) |
| Lifecycle | Disposable; expected to be captured or destroyed |
| User interface | USB-serial tether to a "gateway" node (host: phone/tablet/laptop — TBD) |
| Concealment | Coloured/camouflaged housings (grass-green, ground-black). Delay discovery, do not prevent it |

## 3. Performance targets

| Metric | Target |
|---|---|
| End-to-end throughput | 1,000 English words in ≤10 s (≈600 B/s sustained) |
| End-to-end latency | ≤10 s |
| Per-link range | ≥500 m realistic (NLOS, vegetation) |
| BOM cost per node | <€100 |
| Power | Solar + battery, sized per mission (no fixed limit) |
| Scale | Hundreds of nodes per AO — thousands as a stretch goal |

## 4. Hardware (indicative)

- **MCU**: low-power 32-bit ARM, Meshtastic-class (nRF52 / ESP32-S3).
- **Radio**: multi-band / agile front-end. Sub-GHz ISM as baseline; reserved military bands available (defence project — no civil spectrum constraint).
- **Power**: solar panel + Li-ion or LiFePO4. Capacity sized to mission duration and latitude.
- **Antenna**: integrated omnidirectional.
- **Tether**: USB-C (USB-serial protocol).
- **Housing**: ruggedised, drop-survivable, camouflaged. Sky view required for the panel — accepted visual signature.
- **Tamper sensor**: optional, depends on §6 choice.

## 5. Network

- **Routing**: derived from Meshtastic's flood-and-dedupe baseline. **Open question**: Meshtastic today is tuned for tens of nodes; reaching hundreds–thousands likely requires a hierarchical layer (cluster heads, gateway election) or replacing the routing layer (e.g. BATMAN-adv variant). To be benchmarked early.
- **Cover traffic**: every node transmits at a constant rate. Real messages are statistically indistinguishable from filler. Cost: a large fraction of the airtime budget is "wasted" by design — accepted, since position protection is the core feature.
- **Neighbour discovery**: passive, inferred from cover traffic.
- **Addressing**: gateway-to-gateway; intermediate nodes do not need to interpret content.

## 6. Security model

Two options on the table — **recommendation: B**.

**A. Per-node keys + tamper response.** Each node carries keys; opening the housing zeroises them. Adds BOM cost, mechanical complexity, and a new failure mode (false zeroise on rough handling).

**B. Gateway-only crypto.** Nodes are dumb relays — they cannot decrypt anything. End-to-end encryption lives between gateway operators; key distribution is handled out-of-band. A captured node yields ciphertext and cover traffic, nothing exploitable.

**B** is consistent with the "attritable, even capture-tolerant" thesis and keeps cost down. Routing-layer integrity (preventing injected nodes from poisoning routes) still requires signed routing messages — a lighter primitive than full payload crypto.

## 7. Electronic warfare

- **Frequency agility**: nodes detect jamming (RSSI floor, packet-loss spike) and coordinate a band switch. Coordination protocol TBD — preshared hop schedule vs. negotiated switch.
- **Jammer geolocation**: nodes share RSSI samples; a gateway triangulates the jammer position from the mesh. Useful intelligence by-product, not a hard requirement.
- **Limits**: a wideband barrage jammer with adequate power defeats any cheap node. Scope is explicitly "contested but not saturated" EMS.

## 8. Threat model and mitigations

| Threat | Mitigation |
|---|---|
| Node capture, key extraction | Gateway-only crypto (option B) — nodes hold no useful secret |
| DF of tethered operator | Long tether or place node away from operator's actual position before use |
| Wideband jamming | Out of scope; system targets contested-not-saturated EMS |
| Visual / EO-IR detection | Camouflage; accept attrition, overprovision |
| Traffic analysis | Constant-rate cover traffic |
| Routing-layer injection | Signed routing messages |
| Replay / injection of false data | Per-message authentication at gateway layer |

## 9. Positioning vs alternatives

| System | Cost/node | EW resilience | Bandwidth | Role |
|---|---|---|---|---|
| Meshtastic (stock) | ~€30 | none | low | Hobbyist |
| **This project** | **<€100** | **moderate (FH + cover traffic)** | **low (≈600 B/s)** | **Attritable rear-area / stabilisation comms** |
| Wave Relay, Silvus, Persistent | €10k+ | high | high | Frontline MANET |

A deliberate third point on the cost/capability curve. Not a replacement for hardened MANET at the FLOT.

## 10. Open questions

1. **Routing at scale** — fork Meshtastic or replace its routing layer? Decide after a scale benchmark.
2. **Cover traffic rate vs. battery life** — quantify the trade-off for a representative mission (e.g. 7-day deployment, Belgian winter solar yield).
3. **Frequency plan** — which bands to support in the prototype radio front-end, and which to reserve for AJ hop targets.
4. **Tether host** — phone, ruggedised tablet, bare laptop? Drives the gateway-side software stack.
5. **Acceptable loss rate per mission** — drives density and BOM ceiling.
6. **AJ coordination protocol** — preshared hop schedule (simple, brittle) vs. negotiated switch (robust, complex).
