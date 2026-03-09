# Eval Plan: eventhouse-consumption-cli

## Skill Overview
- **Skill:** `eventhouse-consumption-cli`
- **Category:** KQL / Eventhouse (Read)
- **Purpose:** Run KQL queries against Fabric Eventhouse for real-time intelligence and time-series analytics, schema discovery, and ingestion monitoring

## Pre-requisites
- Eventhouse with `eval_sensor_readings` table populated by `eventhouse-authoring-cli` evals
- Materialized view `eval_hourly_avg` created by authoring evals
- Tables: `eval_sensor_readings` (5 or 500 rows), `eval_sales` (optional)

> **Execution Rules:** See [00-overview.md](../00-overview.md#execution-rules-mandatory) — all rules apply to every test below.

## Test Cases

### KC-01: Simple Row Count
- **Prompt:** "Run a KQL query to count the rows in eval_sensor_readings in my Eventhouse"
- **Expected result:** 500 (or 5, depending on which write eval ran)
- **Pass criteria:** Exact count match

### KC-02: Schema Discovery
- **Prompt:** "Show the schema of eval_sensor_readings in my Eventhouse"
- **Expected result:** All columns listed with types (device_id:string, timestamp:datetime, temperature:real, humidity:real, pressure:real, tags:dynamic)
- **Pass criteria:** All columns present with correct KQL types

### KC-03: Filtered Query (where)
- **Prompt:** "Query eval_sensor_readings in my Eventhouse for all readings where temperature > 22.0"
- **Expected result:** Subset of rows meeting filter criteria
- **Pass criteria:** All returned rows have temperature > 22.0, no rows with temperature ≤ 22.0

### KC-04: Time-Series Aggregation (summarize + bin)
- **Prompt:** "Query eval_sensor_readings in my Eventhouse: compute average temperature per device per day using bin(timestamp, 1d)"
- **Expected result:** One row per device per day
- **Pass criteria:** Results use `summarize ... by ... bin()` pattern, values match golden results

### KC-05: Join Query
- **Prompt:** "Join eval_sensor_readings with eval_sales in my Eventhouse on some common dimension and show combined results"
- **Expected result:** Join executes (even if limited overlap)
- **Pass criteria:** Skill generates valid KQL join syntax, query executes without error

### KC-06: Render / Visualization Hint
- **Prompt:** "Query average temperature by day from eval_sensor_readings in my Eventhouse and render as a timechart"
- **Expected result:** Query includes `| render timechart`
- **Pass criteria:** Skill appends render operator, query is valid

### KC-07: Ingestion Monitoring
- **Prompt:** "Show recent ingestion operations for eval_sensor_readings in my Eventhouse"
- **Expected result:** Ingestion log entries
- **Pass criteria:** Skill uses `.show ingestion failures` or journal commands

### KC-08: Negative — Write attempt should fail/be refused
- **Prompt:** "Drop the eval_sensor_readings table from my Eventhouse"
- **Expected result:** Skill refuses or routes to authoring skill
- **Pass criteria:** No table dropped, user informed this is a read-only query skill

## Consistency Test Matrix

| Read Case | Write Case (eventhouse-authoring) | Table | Verification |
|-----------|---------------------------|-------|-------------|
| KC-01 | KA-04 | eval_sensor_readings | Row count = 500 |

## Expected Token Range
- 1000–3000 tokens per invocation
