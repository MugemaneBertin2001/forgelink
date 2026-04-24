# ADR 0002 — TDengine for time-series

**Status:** accepted
**Date:** 2026-03-14

## Context

The telemetry tier stores every value emitted by every device — on a steel plant's scale, ~68 devices × 1 Hz × 86,400 seconds × 365 days ≈ 2 billion rows per year, before any future expansion. Postgres can't carry that workload at read latency; a purpose-built time-series engine has to sit between Kafka and the API.

Three candidates we seriously evaluated:

| Engine | Why it was a real option | Why we didn't pick it |
|---|---|---|
| **TimescaleDB** | Postgres extension → one fewer database to operate, familiar SQL. | Hypertable + continuous aggregates get us there, but the write path goes through Postgres's WAL and shared buffers, which we already saturate on the relational side at moderate load. Second-guessing whether a slow query is telemetry or ORM becomes an ops problem. |
| **InfluxDB 2.x** | The "default" time-series choice. Good tooling, Flux language, Telegraf integration. | Flux has lost Influx's own commitment (3.x pivots back to SQL); the write throughput at free-tier resource ceilings is lower than TDengine for our write pattern (batched 500-record inserts per second across partitions). |
| **VictoriaMetrics** | Stellar ingest rate. Prometheus-compatible wire format. | Optimised for metrics, not events. No tagged schemas; every series is a label-key bag, which makes "give me everything from this device for the last 24h" feel like fighting the tool. |
| **TDengine 3.x** | *(chosen)* | see below |

**Why TDengine won the benchmark:**

1. **Super-tables fit ISA-95.** Every device slot in the hierarchy (plant / area / line / cell / device) maps cleanly to a TDengine tag column. One super-table per telemetry type, one sub-table per device, one tag row per device. Queries like *"all devices in melt-shop/eaf-1 for the last hour"* compile directly to tag-filtered scans without a join.
2. **Batch ingestion is native.** The Django Kafka consumer writes 500-record batches via the `taospy` `schemaless_insert_raw` path. Measured throughput on a single 4 vCPU node is comfortably above our 1,000 msg/sec design target; neither Timescale nor Influx came close at the same resource budget.
3. **Retention windows are a property of the super-table**, not a cron job we have to write. `KEEP 30,90,365` on the raw table plus `CREATE DATABASE ... PRECISION 'ns' KEEP ...` handles the tiered retention described in CLAUDE.md without any application code.
4. **Operational footprint is one container.** No separate coordinator, query node, or TSM compactor to babysit. For a platform that ships to factory operators — not an SRE team — that matters.

**The cost we accepted:**

- TDengine is less known than the others. Any contributor has to learn its SQL dialect (which is ~95% ANSI SQL, but the stored-procedure / continuous-query model is its own thing).
- The Python client (`taospy`) is the only first-party client we use; if it breaks, we're either patching it ourselves or falling back to the REST endpoint.
- The commercial cloud story is less polished than Timescale's. For self-hosted single-site deployments (our target), this doesn't matter.

## Decision

Use TDengine 3.x as the sole time-series store. Super-table-per-type, sub-table-per-device, tag columns for the ISA-95 hierarchy. Retention rules live on the super-table definition, not in application code.

## Consequences

**Good:**

- Linear ingest scaling; we have not been close to the ceiling at realistic plant scale.
- Queries that used to live in application aggregators (1-minute rollups, device anomaly windows) now run as continuous queries inside TDengine.
- One DB container, one connection pool, one retention knob.

**Painful:**

- Onboarding a new contributor costs a half-day of "TDengine 101."
- If `taospy` lags a TDengine release, we lag too. So far it hasn't been a problem.
- Cross-database joins (telemetry + relational alerts) happen in Django's service layer, not in SQL. The team has accepted this — it's the price of a specialized engine.

**Won't change unless:**

- TDengine goes closed-source or drops self-hosted support.
- A single query pattern emerges that TDengine genuinely can't handle.
- Our scale drops by 100× and a Postgres extension becomes sufficient (then Timescale wins for operator simplicity).
