# AVEVA PI → TDengine Migration Playbook

**Last updated:** 2026-04-22

This is a playbook for migrating a PI System deployment (PI Data Archive + PI Asset Framework) onto a ForgeLink-style architecture: TDengine for time-series storage, an ISA-95 Unified Namespace on MQTT for real-time distribution, and Kafka for the analytics pipeline. It is deliberately generic — a real engagement starts with source-side discovery and produces a scoped SOW. The patterns here are what we apply across that SOW; the specifics are tuned on each project.

We name products by their historical names (PI Data Archive, PI Asset Framework, PI Web API, PI OPC-UA Server, PI Vision). AVEVA has rebranded some of these under the AVEVA PI System product line; the technical architecture has not materially changed from the pre-acquisition era, so the patterns below remain applicable. Verify current product naming and version compatibility against the target deployment.

## 1. Scope and assumptions

We address the following PI deployments:

- **PI Data Archive** — the historian holding time-series values (PI Points).
- **PI Asset Framework (PI AF)** — the object model (Elements, Attributes, Templates, Event Frames) layered on top of the Data Archive.
- Any supported combination of PI Web API, PI OPC-UA Server, and the PI System Explorer tooling used to navigate AF.

We explicitly do not address the following in this playbook (see [Section 8](#8-what-this-playbook-does-not-cover) for reasoning):

- PI Vision dashboards and display migration.
- PI Asset Analytics (calc engine on AF) — migrating calcs is a separate, larger workstream.
- PI Notifications — event-driven notification rules.
- PI Integrator for Business Analytics.
- ProcessBook file conversion.

Assumptions the playbook makes about the target ForgeLink environment:

- TDengine is provisioned with the supertable design described in [`tdengine-schema.md`](../architecture/tdengine-schema.md).
- The Unified Namespace grammar follows [`uns-topic-hierarchy.md`](../architecture/uns-topic-hierarchy.md): `forgelink/<plant>/<area>/<line>/<cell>/<device_id>/<message_type>`.
- An MQTT broker (EMQX) enforces ACL by area; an MQTT→Kafka bridge lands data in Kafka topics partitioned by area; a Kafka consumer (`services/django-api/apps/telemetry/kafka_consumer.py`) batches writes into TDengine.

## 2. Source-side discovery

Before any mapping or export, we inventory the PI System. Every subsequent decision depends on this inventory.

**Minimum discovery checklist:**

| Item | Why it matters |
|---|---|
| PI Point count, by `pointtype` | Storage sizing, type mapping to TDengine columns |
| AF database count and total Element count | Hierarchy-mapping effort |
| AF hierarchy depth (max and p95 path length) | UNS topic-grammar headroom |
| Attribute count per Element Template | Per-device column count in TDengine |
| Event Frame templates and annual event-frame volume | Scope decision (in or out of migration) |
| PI Point compression settings per tag (or per template) | Validation tolerance (see subsection below) |
| Historian retention configured per archive | Backfill window sizing |
| Active PI Web API / OPC-UA consumers | Downstream cutover coordination |
| Tag naming conventions in use | UNS device_id grammar decisions |

We produce this inventory as a spreadsheet (or a small SQL extract from PIFD) rather than as prose — it becomes the reference artefact for every subsequent decision.

### Compression and why the archive is not the ground truth

This is the single most important concept in a PI migration, and the one first-time migrators routinely miss.

PI applies server-side filtering before writing to the archive. Two filters stack:

1. **Exception filtering** (configured per tag via `excdev`, `excmax`, `excmin`). Applied in the PI interface process (or the client writing to PI). Values within the exception deadband of the last reported value are suppressed before they reach the archive.
2. **Compression filtering** (configured per tag via `compdev`, `compmax`, `compmin`). Applied in the Data Archive on write. The archive keeps only values that exceed the compression deviation relative to a running slope — a form of swinging-door compression.

The consequence: **the PI archive does not contain every reading the sensor produced.** It contains the compression-filtered subset that PI considered worth storing. On typical deployments, compression filters 70–95% of incoming values; the exact ratio depends on process dynamics and per-tag settings.

This reframes the validation problem. We are not comparing TDengine against raw sensor output — the raw sensor output was never stored in PI in the first place. We are comparing TDengine against PI's compression-filtered view. Any validation query must apply the same retrieval mode on both sides ([see Section 7](#7-validation-and-reconciliation)).

Discovery step for compression: export the compression configuration for every tag in scope. The PI AF SDK or PI Web API can both enumerate `compdev` / `compmax` / `compmin` / `excdev` / `excmax` / `excmin` per point. We tabulate this alongside the tag inventory and flag tags with `compressing = off` separately — those tags store every reading and will have wildly different data volumes than compressed tags.

**Output of source-side discovery:** a tag inventory with name, type, engineering units, compression settings, AF path, and downstream consumer list. Without this, every later step is guessing.

## 3. Mapping: PI AF → ISA-95 UNS

We translate PI AF paths into ForgeLink UNS topics at attribute granularity. The mapping is two-sided: each AF Element becomes one or more UNS hierarchy segments, and each AF Attribute becomes a device publishing on a topic.

### Mapping rules

| PI AF construct | ForgeLink UNS segment | Notes |
|---|---|---|
| AF Database | *(implicit — one UNS root per database)* | If multiple AF databases exist, each maps to a distinct UNS root or shares a root with a database-prefixed area. |
| AF Element at depth 1 | `<plant>` | Typically a plant-level element. |
| AF Element at depth 2 | `<area>` | Process area (melt shop, continuous casting, etc.). |
| AF Element at depth 3 | `<line>` | Production line within area. |
| AF Element at depth 4 | `<cell>` | Equipment cell. |
| AF Element at depth 5+ | `<device_id>` segment | If AF hierarchy is deeper than 4 levels, depth-5 elements collapse into device_id prefix; deeper paths become device_id suffixes separated by `-`. |
| AF Attribute on an Element (with PI Point reference) | One `<device_id>` + `<message_type>` pair | The attribute becomes a distinct device in ForgeLink's asset registry. |
| AF Attribute that is a calculated/formula attribute | Not migrated as a device — migrate as a ForgeLink AlertRule or a TDengine view | Calcs are a separate workstream. |
| AF Element Template | Maps to a ForgeLink DeviceType (`apps/assets/models.py:DeviceType`) | Template attributes define the device_type's default unit, typical range, etc. |
| AF Event Frame | Maps to a ForgeLink Alert or AuditEvent | Out of scope for v1; flag for follow-up. |

### Worked example

PI AF path:

```
\\PI-AF-Server\SteelCorp\Plant1\Melt Shop\EAF-1\Electrode A|Temperature
```

AF breakdown:
- AF Server: `PI-AF-Server`
- AF Database: `SteelCorp`
- Element path: `Plant1 → Melt Shop → EAF-1 → Electrode A`
- Attribute: `Temperature` (referenced to PI Point `AA-EAF1-ELA-T001` with `engunits = °C`)

ForgeLink asset registry entries (per `apps/assets/models.py`):

| Model | code | name |
|---|---|---|
| `Plant` | `steel-plant-kigali` | Plant 1 |
| `Area` | `melt-shop` | Melt Shop |
| `Line` | `eaf-1` | EAF-1 |
| `Cell` | `electrode-a` | Electrode A |
| `DeviceType` | `temperature-sensor` | (from AF Element Template) |
| `Device` | `temp-sensor-001` | EAF-1 Electrode A Temperature |

ForgeLink UNS topic (per `uns-topic-hierarchy.md`):

```
forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/telemetry
```

Telemetry payload published per reading:

```json
{
  "device_id": "temp-sensor-001",
  "timestamp": "2026-04-22T14:30:00.123Z",
  "value": 1547.3,
  "unit": "celsius",
  "quality": "good",
  "sequence": 10482
}
```

The `sequence` field supports gap detection during validation; it is monotonically increasing per device and is populated either from PI's archive sequence (if preserved during export) or from the MQTT bridge on live cutover.

### Naming normalization

PI tag names vary wildly across deployments. We convert tag names to ForgeLink `device_id` values using a deterministic normalization rule agreed with the customer before export begins: lowercase, non-alphanumerics to `-`, collapse repeats, strip leading/trailing `-`. We commit the mapping from original tag name to `device_id` to version control; the reverse mapping becomes the reconciliation key during validation.

### Timezone handling

PI stores timestamps in UTC internally but surfaces them as server-local time through many client tools. The ForgeLink pipeline expects UTC with ISO-8601 timezone suffix. We convert on export, not on ingest — inconsistent UTC handling at ingest time is one of the top three sources of migration bugs.

## 4. Data export strategies

### Retrieval mode — the decision that shapes export strategy

Before picking an export strategy, we pick a retrieval mode. The PI Web API exposes three, and each has different semantics:

| Mode | PI Web API resource | What it returns | When to use |
|---|---|---|---|
| **Recorded** | `/streams/{webId}/recorded` | The exact values PI stored in the archive, post-compression | Default for backfill. Preserves archive fidelity; TDengine will contain what PI contains. |
| **Interpolated** | `/streams/{webId}/interpolated` | Evenly-spaced values, server-interpolated between recorded values | Use only when downstream analytics has strict even-spacing requirements. Introduces synthetic data. |
| **Plot** | `/streams/{webId}/plot` | Min/max/start/end per time bucket, optimized for visualization | Rarely the right choice for migration. Loses resolution for analytics. |

**Our default:** Recorded data for backfill, live OPC-UA subscriptions for the cutover phase. Interpolated is justified only when an existing downstream consumer — a dashboarding tool, a report, an analytics model — requires evenly-spaced samples and cannot be changed. Plot is never correct for migration.

This decision must be made and recorded before any export code is written. Changing retrieval mode mid-migration invalidates every validation run.

### Option 1: PI Web API bulk export (Recorded)

Natural fit for backfill. REST-over-HTTPS, paginated, batchable via `/batch`. The pattern:

1. Authenticate against PI Web API (typically Kerberos or basic auth).
2. Resolve each in-scope PI Point to its `WebID` by path lookup (`GET /points?path=\\server\tagname`).
3. For each WebID, page through `GET /streams/{webId}/recorded?startTime=...&endTime=...&maxCount=N` in time windows sized to stay under the server-side result limit.
4. Translate each returned record into the ForgeLink telemetry payload and land it in TDengine using the Kafka consumer's batch-write path.

Sketch (illustrative; exact parameter names should be verified against the target PI Web API version):

```python
# Pattern for bulk export via PI Web API.
# Package names are generic; use whichever PI Web API client the target deployment standardizes on.

def export_tag_recorded(session, web_id, start, end, window_hours=6):
    """Yield recorded values for a PI Point, paginated by time window."""
    window = timedelta(hours=window_hours)
    cursor = start
    while cursor < end:
        window_end = min(cursor + window, end)
        resp = session.get(
            f"{PI_WEB_API}/streams/{web_id}/recorded",
            params={
                "startTime": cursor.isoformat(),
                "endTime": window_end.isoformat(),
                "maxCount": 150_000,  # stay under server limit
                "selectedFields": "Items.Timestamp;Items.Value;Items.Good;Items.Questionable",
            },
            timeout=120,
        )
        resp.raise_for_status()
        for item in resp.json()["Items"]:
            yield {
                "timestamp": item["Timestamp"],
                "value": item["Value"],
                "quality": "good" if item["Good"] else "bad",
            }
        cursor = window_end
```

Tradeoffs:
- **Pros:** standards-based, auditable, paginable, concurrent across tags.
- **Cons:** slow for 100k+ tag backfills (PI Web API is a REST overlay on the Data Archive, not a bulk-export engine). Large backfills run in parallel across many tags and still take hours to days.

### Option 2: PI Web API + pandas (ETL pattern)

The same PI Web API surface wrapped as a Python library (`piwebapi`, `osisoft-pidevclub-piwebapi`, or a similar community package — we do not pin a specific package here; the target deployment's existing tooling typically dictates the choice) and composed with pandas for in-memory transforms.

Useful when the export also needs to normalize units, reshape payloads to match TDengine tag columns, or join against AF attribute metadata before ingest. Effectively Option 1 with a pandas-shaped transform stage.

Tradeoffs:
- **Pros:** scriptable, Python-native, natural for ETL transforms.
- **Cons:** still bound by PI Web API performance. Pandas adds memory pressure at 10M+ rows; use chunked iteration or Polars for large tags.

### Option 3: PI OPC-UA subscription (live cutover)

Standards-based, real-time. The PI OPC-UA Server product exposes the AF hierarchy and PI Point values as an OPC-UA address space. A ForgeLink-side OPC-UA client (we already ship one: `services/edge-gateway/`) subscribes to value changes via OPC-UA MonitoredItems and republishes to MQTT under the ForgeLink UNS grammar.

This is the mechanism for the live phase of cutover, not for backfill. Historical values before subscription start are not delivered by OPC-UA subscription; that is what Option 1 handles.

Tradeoffs:
- **Pros:** real-time, standards-based, no bespoke PI integration code (we reuse our existing OPC-UA client).
- **Cons:** requires the PI OPC-UA Server product to be installed and licensed on the source side. Namespace layout is configurable per deployment — node IDs must be mapped to UNS topics during setup. Verify namespace layout against the target PI OPC-UA Server configuration.

### Strategy recommendation

For most migrations we combine Option 1 (Recorded backfill) with Option 3 (OPC-UA live cutover). Option 2 is layered on when the transform stage is non-trivial. A decision to use any single option in isolation is worth questioning; the common failure mode is running Option 1 for live cutover and accepting the resulting 1–5 minute lag as acceptable, which it usually is not for alerting.

## 5. TDengine ingestion pattern

ForgeLink's telemetry landing table is the `telemetry` supertable defined in [`tdengine-schema.md`](../architecture/tdengine-schema.md). Every exported value, whether from backfill or live cutover, lands in this table with the same column set.

### Tag column mapping

| TDengine tag column (from `tdengine-schema.md`) | Source |
|---|---|
| `device_id` | ForgeLink device code (derived from PI tag name during mapping) |
| `plant` | UNS plant segment |
| `area` | UNS area segment |
| `line` | UNS line segment |
| `cell` | UNS cell segment |
| `unit` | PI Point `engunits` attribute, normalized (e.g., `DegC` → `celsius`) |
| `device_type` | From AF Element Template (maps to ForgeLink `DeviceType.code`) |

### Batch insert rule

TDengine writes are batched: **500 records or 1 second**, whichever comes first. This rule is enforced in the Django telemetry pipeline (`services/django-api/apps/telemetry/tdengine.py`) and the Kafka consumer path (`services/django-api/apps/telemetry/kafka_consumer.py`). The migration tooling must honor the same rule — per-record inserts will saturate the TDengine client connection pool long before they saturate TDengine itself.

### Backfill vs. live topology

**Backfill path:**

```
PI Web API (Recorded) → Python exporter → Kafka topic (telemetry.<area>)
                                              → TDengine Kafka consumer → TDengine
```

Going through Kafka (rather than direct TDengine insert from the exporter) gives us:
- Replay capability if an ingest window fails.
- Identical code path as live cutover, so validation runs against the same pipeline.
- Back-pressure when TDengine is busy.

**Live path:**

```
PI OPC-UA Server → ForgeLink edge-gateway (OPC-UA client) → EMQX (MQTT) → MQTT bridge → Kafka → TDengine
```

Same Kafka consumer, same TDengine writes. The only production difference from backfill is the front of the pipeline.

### Retention and compression on the TDengine side

TDengine retention per `tdengine-schema.md`: raw for 30 days, 1-minute aggregates for 90 days, 1-hour aggregates for 1 year, 1-day aggregates indefinitely. Backfilled data older than 30 days lands only in the aggregate tables, not the raw supertable, unless the retention policy is temporarily extended for the backfill window.

If the source PI deployment has longer raw retention than 30 days and the migration is expected to preserve that raw retention, the TDengine retention policy must be adjusted **before** backfill starts. Changing retention after raw data has been ingested causes the already-ingested records to expire per the new policy.

## 6. Cutover strategy

Cutover is the phase where TDengine becomes the authoritative telemetry store and PI is demoted to a fallback. We run it in four phases, with explicit criteria for advancing between phases.

### Phase 0 — Parallel backfill

Backfill runs in isolation. Only the migration team has access to TDengine's telemetry. PI remains the production system. Duration: as long as the backfill takes (hours to weeks depending on tag count and retention window).

**Exit criteria:** all in-scope tags backfilled for the agreed retention window with validation queries passing (see Section 7).

### Phase 1 — Dual-write

PI continues to serve as the production system. Live values also flow into TDengine via the PI OPC-UA subscription path. Downstream consumers (dashboards, alerts, analytics) still read from PI. Duration: **minimum 14 days of stable operation** before advancing.

**Monitoring during dual-write:**
- Gap detection on TDengine side: any missing sequence number per device triggers an alert.
- Lag monitoring: end-to-end latency from PI value change to TDengine write, p95 and p99 per device.
- Validation queries run hourly comparing rolling windows on both sides.

**Exit criteria:** all three of the following hold for 14 consecutive days:
1. **Agreement tolerance met.** Per-tag hourly count agreement within ±0.5%, hourly mean agreement within ±0.1% for analog tags (tighter for digital). Tolerance is per-tag, not averaged across tags.
2. **No unresolved validation failures.** Any tag with sustained disagreement is root-caused (timezone, compression, unit, naming) and either fixed or explicitly excluded from the migration scope.
3. **Lag stability.** p95 live-path latency under 5 seconds, p99 under 30 seconds, with no upward trend.

### Phase 2 — Cutover

Downstream consumers are redirected from PI to TDengine (via the ForgeLink Django API). PI continues to run in parallel but no longer serves production traffic. Duration: **minimum 7 days** before Phase 3.

**Rollback trigger during Phase 2:** any of the following reverts consumers to PI:
- TDengine write errors sustained above 0.01% of incoming records for more than 15 minutes.
- Query-side availability drops below 99.5% for any consumer in a 1-hour window.
- Validation diff exceeds the Phase 1 tolerance for more than 5% of tags.

Rollback is a reversible routing change at the consumer layer, not a restore — the dual-write path keeps PI current.

### Phase 3 — Decommission source writes

PI stops receiving live writes. PI OPC-UA Server can remain running for read-only historical access if desired, or the Data Archive can be archived off to long-term storage. This phase ends the migration.

### Cutover decision matrix

| Evidence | Threshold | Action |
|---|---|---|
| Per-tag hourly count disagreement | >0.5% for 4 consecutive hours | Investigate; do not advance phase |
| Per-tag hourly mean disagreement (analog) | >0.1% for 4 consecutive hours | Investigate |
| Per-tag hourly mean disagreement (analog) | >0.5% any single hour | Investigate if trend |
| Unexplained gap on TDengine side | Any gap >60s on non-event-driven tag | Investigate before next phase |
| Live-path p99 latency | >30s sustained 15 min | Block phase advance |
| Rolling 24h validation pass rate | <99% of tags | Hold phase |
| All above healthy | 14 days Phase 1, 7 days Phase 2 | Advance |

## 7. Validation and reconciliation

**Calibration before writing any queries:** we are not validating that TDengine matches every reading the sensor produced. We are validating that TDengine reproduces PI's compression-filtered view within a defined tolerance. These are different problems. The first is usually impossible — the raw sensor output was never stored in PI. The second is the migration's actual job, and it is tractable.

Every validation query below applies the **same retrieval mode on both sides**. If we backfilled from PI Recorded data, we validate against PI Recorded data — never against Interpolated.

### Validation query set

**Count per tag per day.** For each in-scope tag, compare the count of values in each day bucket on PI (Recorded) vs. TDengine. Expected agreement: within 0.5% per tag per day. Disagreement indicates missed time windows in backfill, dropped records in the live path, or a timezone bug.

```sql
-- TDengine side
SELECT device_id, CAST(ts AS DATE) AS day, COUNT(*) AS n
FROM forgelink_telemetry.telemetry
WHERE device_id IN (...)
  AND ts >= :start AND ts < :end
GROUP BY device_id, day;
```

The PI-side equivalent is a PI Web API `/streams/{webId}/summary` query with `summaryType=Count` and daily intervals, run per tag. Results are joined by `(device_id, day)` in the reconciliation script.

**Statistical summary per tag per hour.** Per tag, compute `min`, `max`, `avg`, and `stddev` on hourly windows over the validation period. Analog tags should agree within ±0.1% on mean; ±1% on standard deviation (stddev is more sensitive to single-outlier differences). Digital tags use exact-match on transition counts instead.

**Gap detection across sequence numbers.** For every (device_id, hour) pair, check that the TDengine-side sequence numbers are dense (no gaps beyond the expected per-tag scan interval). Gaps in backfilled data mean an export window failed silently and was not retried.

**Quality code reconciliation.** PI quality codes (Good, Bad, Questionable, Substituted, etc.) map to our simplified `good / bad / uncertain` taxonomy. We compare quality-code transition counts per tag per day. Deviation indicates mapping rule drift.

**Compression setting audit.** For every tag, confirm that the PI-side `compressing` flag and the deviation settings have not changed during the migration window. Compression setting changes mid-migration invalidate every prior validation run. We snapshot compression settings at backfill start and re-check at cutover.

### Reconciliation script structure

We run validation as a scheduled job, not as a one-shot command. The job:

1. Pulls the tag manifest (in-scope tags + their compression settings).
2. For each tag, runs all five validation queries against a sliding window.
3. Writes per-tag, per-window results to a dedicated TDengine supertable (`migration_validation`) and to a relational summary table.
4. Raises alerts on threshold breach.

The validation results supertable becomes the audit trail that justifies the cutover decision. Without it, "we ran validation" is an assertion; with it, it's evidence.

## 8. What this playbook does not cover

Each of these is a real workstream with its own scope. We name them explicitly so they are not confused with in-scope migration work.

- **PI Asset Analytics calculations.** The calc engine on AF (formulas, rollups, expression evaluations). Migrating calcs requires translating AF Analytics expressions into either ForgeLink AlertRules, Django Celery tasks, or TDengine continuous queries. The translation is per-calc and benefits from native-speaker review of both sides. Budget it as a separate workstream.
- **PI Vision displays.** Dashboard migration. ForgeLink's dashboarding path is Grafana (planned for v1.1.0) or the Flutter mobile app. PI Vision displays are XAML-adjacent and do not translate mechanically. Expect to rebuild dashboards from requirements, not from source.
- **PI Notifications.** Event-driven notification rules on AF. Maps to ForgeLink AlertRules conceptually, but the rule grammar is different. Treat as a separate workstream with a ForgeLink-side rebuild from requirements.
- **PI Integrator for Business Analytics.** The BI-facing data flattening layer. If the target analytics stack changes during migration (e.g., moving from PI BA to a warehouse + BI tool), that's a data-warehousing project alongside this one.
- **ProcessBook file conversion.** Legacy display format. Treat as requirements-only migration.
- **PI Event Frames.** Time-bounded occurrences (batches, downtime, alarms). Map to ForgeLink `Alert` + `AlertHistory` or to a dedicated event store. Worth calling out separately because the volume is often large (tens of thousands of event frames per year) and the mapping is non-trivial. We recommend a separate sub-project rather than folding it into the initial tag migration.
- **Custom PI interfaces.** If the PI deployment ingests data via custom PI interfaces (OPC-DA, Modbus, serial, bespoke), the interface itself is out of scope — the ForgeLink-side equivalent is an OPC-UA client, an MQTT bridge, or a Kafka connector, chosen per source protocol.

Explicit non-scope is a feature of a well-run migration, not an admission of limitation. Projects that silently absorb these items into the main migration miss their dates.

## 9. Cost and timeline heuristics

**These are planning heuristics for initial SOW sizing, not commitments. Actual project scope is set after source-side discovery.** The ranges below assume a two-person migration team (one senior, one mid-level) with customer-side SME availability for tag-naming decisions and cutover coordination.

| Size | Tag count | Person-weeks | Rough infra cost (backfill phase only) |
|---|---|---|---|
| Small | 1,000 tags | 4–8 | Single TDengine node (8 vCPU / 32 GB), ~$200–$500/month |
| Medium | 10,000 tags | 12–20 | TDengine cluster (3 nodes), ~$1–$3k/month |
| Large | 100,000+ tags | 24–40+ | TDengine cluster (5+ nodes), ~$5–$15k/month, plus dedicated Kafka cluster |

**Factors that move a project up or down within its size range:**

1. **AF hierarchy depth and consistency.** Uniform 4-level hierarchies map mechanically. Mixed-depth or inconsistent hierarchies (some tags at depth 3, others at depth 7) require per-tag mapping rules and expand scope substantially.
2. **Compression-setting complexity.** If compression is uniform across tag families, validation tolerance is simple. If compression is tuned per-tag by a domain expert over years, every tag may need its own tolerance and the validation phase lengthens.
3. **Downstream consumer count.** Every consumer (dashboard, alert rule, report, analytics model, integration) is a cutover coordination point. Five consumers is weeks; fifty consumers is months. This is usually the dominant factor on the right side of the range.
4. **Event Frames in or out of scope.** In-scope event frames add 20–40% to the estimate depending on annual volume and template complexity.
5. **Source-side stability.** A PI deployment that is actively being modified during migration (tags added, hierarchy changed, compression retuned) will slip. We recommend a change-freeze on the PI side from Phase 0 through Phase 2.

Ranges narrow significantly after discovery. The first deliverable of a real engagement is a discovery report that converts these ranges into a specific estimate.

---

## Related docs

- [ROADMAP.md](../../ROADMAP.md) — where migration tooling features land across ForgeLink releases
- [Architecture overview](../architecture/overview.md) — the ForgeLink target architecture this playbook maps onto
- [UNS topic hierarchy](../architecture/uns-topic-hierarchy.md) — the target grammar for PI AF → UNS translation
- [TDengine schema](../architecture/tdengine-schema.md) — the target time-series schema and ingest rules
- [Zero Trust architecture](../architecture/zero-trust.md) — security posture for the migrated environment
