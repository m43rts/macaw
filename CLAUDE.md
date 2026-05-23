# both3

Disposable mesh comms for contested zones — Meshtastic fork hardened for defence use (frequency agility, cover traffic, gateway-only crypto).

## Context

- **Pitch**: [pitch.md](pitch.md) — one-page elevator pitch.
- **Spec**: [spec.md](spec.md) — concept, performance targets, threat model, open questions.
- **Upstream**: [meshtastic/](meshtastic/) — vendored Meshtastic firmware we are forking.

## Project status

Hackathon prototype, **2-day timeline**. Scope decisions should favour demonstrable end-to-end behaviour over completeness. Cut anything not on the demo path.

## Hardware

Testing exclusively on **Heltec LoRa 32 v3** (ESP32-S3 + SX1262). Pick the matching `heltec-v3` PlatformIO env when building; ignore other board variants unless asked.
