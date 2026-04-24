# ADR 0003 — UNS topic design (ISA-95)

**Status:** accepted
**Date:** 2026-03-14

## Context

Every telemetry / event / status message has to land on an MQTT topic that downstream consumers can filter, route, and authorize against. A topic grammar is a public API of the platform — every device firmware, every bridge, every alert rule binds to it. Getting it wrong means either rebuilding the whole device fleet or living with the scar forever.

The industry hands us [ISA-95](https://en.wikipedia.org/wiki/ISA-95) as a naming framework: Enterprise → Site → Area → Work Cell → Equipment. The question is how literally to translate that into MQTT topic segments.

Options we considered:

1. **Flat device-ID topics** — `forgelink/temp-sensor-001/telemetry`.
   Simple, but every authorization / routing rule has to maintain its own device-to-location lookup. EMQX ACL is also much harder to express ("operator can subscribe to melt-shop devices" becomes "list every ID").
2. **Type-first topics** — `forgelink/telemetry/melt-shop/eaf-1/temp-sensor-001`.
   Nicer for a subscriber that wants all telemetry, worse for one that wants all signals from one device.
3. **Location-first, ISA-95-shaped** — `forgelink/<plant>/<area>/<line>/<cell>/<device>/<type>`. *(chosen)*
4. **Use Sparkplug B directly** — proper namespace, birth/death certificates, metric aliases.
   We respect it, but it's a protocol unto itself; mandating Sparkplug on every vendor device would either lock us to MQTT clients that speak it or force an aggressive normalization layer we don't want to own.

**Why #3 won:**

- **Matches EMQX ACL semantics.** `forgelink/+/melt-shop/#` is the exact string needed to grant melt-shop operators subscribe access. No lookup table; the ACL engine does it.
- **Aligns with TDengine tag columns** (see [ADR 0002](0002-tdengine-for-timeseries.md)). The same five tags that carve a topic also carve a super-table query.
- **Human-readable in logs.** A flat grep of `docker compose logs forgelink-mqtt-bridge | grep forgelink/steel-plant-kigali/continuous-casting/caster-1` returns exactly the conversation you'd expect.
- **One regex pins the whole grammar.** `services/mqtt-bridge/bridge/mqtt_client.py` has exactly one regex (`UNS_PATTERN`) that every incoming topic is matched against; mismatches go to `dlq.unparseable`. Grammar drift is caught by a single unit test.

**The type suffix decision** (`telemetry` / `status` / `events` / `commands`) was deliberately kept as the *last* segment rather than the first. Reasons:

- Most alert rules and most dashboards want *all* signals from one device. Keeping the type at the tail means a single-device subscription (`.../+`) naturally captures everything.
- Kafka routing in the bridge picks the type off the last path segment — trivial string split, no regex.
- The small cost: "all telemetry across areas" requires a wildcard in the last position (`forgelink/+/+/+/+/+/telemetry`). We accepted this because the subscriber for that query is almost always the MQTT bridge itself, which already does full-fleet subscribe.

**What we deliberately did NOT do:**

- No `data/cmd/evt` three-letter abbreviations. Readability wins at this scale.
- No numeric device IDs in the topic. Kebab-case device names (`temp-sensor-001`) are what appears in Django, TDengine, Grafana, and every log — one form throughout.
- No "environment" prefix (`prod/forgelink/...`). Environment lives in the Kafka cluster name / DNS, not in the topic itself.

## Decision

The UNS hierarchy is `forgelink/<plant>/<area>/<line>/<cell>/<device_id>/<type>` where `type ∈ {telemetry, status, events, commands}`. The regex in `services/mqtt-bridge/bridge/mqtt_client.py` is the grammar's only source of truth; changes to either the regex or `docs/architecture/uns-topic-hierarchy.md` must land in the same commit as the other.

## Consequences

**Good:**

- EMQX ACL rules stay short (`forgelink/+/melt-shop/#`).
- TDengine queries reuse the same five dimensions.
- Unparseable messages land in `dlq.unparseable` with their original topic, so a rogue device firmware surfaces loudly instead of silently dropping.

**Painful:**

- Devices that genuinely don't fit the hierarchy (a plant-wide flow meter that isn't "in" any area) currently get an awkward `_unassigned` cell. Not elegant.
- Adding a new hierarchy level (e.g. a sub-cell) would require either squeezing it into the existing 5-segment middle or cutting a v2 topic grammar.
- The `e-a-f1` kebab-case quirk in `services/edge-gateway/gateway/bridge.py` (see the flag comment in `test_bridge.py`) is a bug in the converter that produces *valid-to-the-regex* but *device-ID-incorrect* topics. Tracked; not yet fixed because the fix breaks round-trip with OPC-UA path names.

**Won't change unless:**

- A customer deploys to a plant that genuinely doesn't map to ISA-95 (rare for steel).
- MQTT 5 user properties become the norm for routing metadata — which would let us flatten the hierarchy into a single canonical ID + properties. Still feels like over-engineering today.
