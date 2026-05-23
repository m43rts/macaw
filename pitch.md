# Disposable Mesh Comms for Contested Zones

**Idea.** Scatter hundreds of cheap (<€100), solar-powered radio nodes across an AO. They self-organise into a mesh. Troops plug into any node via USB-serial — they themselves emit nothing.

**Why it matters.**
- **Attritable**: a precision munition costs more than killing ten nodes.
- **Position-protecting**: constant-rate cover traffic hides *who* is actually transmitting and from *where*. Adversary DF reveals the mesh, not the user.
- **No logistics**: solar + battery, throw-and-forget — UAS drop or hand-thrown.
- **EW-resilient (graceful, not absolute)**: nodes hop frequencies when jammed and triangulate the jammer from shared RSSI.
- **Even capture-tolerant**: nodes can be dumb relays — only gateway operators hold keys, so a recovered node yields ciphertext + filler.

**Performance target.** 1,000 English words end-to-end in ≤10 s, ≥500 m per link, BOM <€100.

**Approach.** Fork `Meshtastic` (proven open-source LoRa mesh) and harden it for defence: frequency agility, cover traffic, gateway-only crypto, camouflaged housings.

**Positioning.** Third point on the cost/capability curve, between Meshtastic (cheap, indefensible) and Wave Relay-class MANET (capable, €10k+/radio). Built for rear-area, stabilisation, and position-denial — *not* a frontline EW substitute.
