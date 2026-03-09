# Regression Analysis

**Current Run:** 2026-02-27 — Workspace: FabricCLITest (`f092f1bd-8c2d-4ac4-bd1b-84226d4bba58`)
**Baseline:** 2026-02-19 — Workspace: skills-for-fabric (`c92c724b-cca6-4b91-b330-548b482c3800`) — [GitHub](https://github.com/microsoft/skills-for-fabric/blob/main/tests/full-eval-tests/result/eval-results.md)

> **Note:** The baseline ran on a Starter Pool capacity workspace. The current run used a different workspace (FabricCLITest), which may explain improvements in previously infrastructure-limited tests.

---

## Verdict: BETTER — all 3 baseline failures fixed, new skills and combined evals added, pass rate improved

---

## 1. Overall Pass Rate

| Metric | Baseline (Feb 19) | Current (Feb 27) | Delta |
|--------|-------------------:|------------------:|------:|
| Total Tests | 74 | 79 | +5 |
| Pass | 54 | 78 | +24 |
| Fail | 3 | 0 | -3 |
| Error | 0 | 1 | +1 |
| Skip | 17 | 0 | -17 |
| **Pass Rate** | **94.7%** | **98.7%** | **+4.0pp** |

> Pass Rate = Pass / (Pass + Fail + Error), excluding skipped tests.

---

## 2. Per-Skill Comparison

### Individual Skills

| Skill | Baseline | Current | Change |
|-------|----------|---------|--------|
| check-updates | 100% (4P/0F/1S) | — (not in current run) | Removed from eval suite |
| spark-authoring-cli | 88.9% (8P/1F/1S) | 100% (9P/0F/0E) | +11.1pp — SA-04 fixed, SA-10 now tested |
| spark-consumption-cli | 100% (7P/0F/3S) | 100% (3P/0F/0E) | Pass rate same; suite restructured (7->3 individual tests) |
| sqldw-authoring-cli | 77.8% (7P/2F/3S) | 100% (9P/0F/0E) | +22.2pp — DWA-07 (time travel) and DWA-08 (transaction rollback) now pass |
| sqldw-consumption-cli | 100% (7P/0F/5S) | 100% (7P/0F/0E) | Pass rate same; previously skipped tests now executed or restructured |
| eventhouse-authoring-cli | 100% (10P/0F/2S) | 91.7% (11P/0F/1E) | -8.3pp — KA-04 changed from SKIP to ERROR (same infra gap) |
| eventhouse-consumption-cli | 100% (11P/0F/2S) | 100% (8P/0F/0E) | Pass rate same; suite restructured (13->8 individual tests) |
| powerbi-authoring-cli | — | 100% (5P/0F/0E) | NEW skill |
| powerbi-consumption-cli | — | 100% (8P/0F/0E) | NEW skill |

### Combined Skills (all new in current run)

| Eval Plan | Tests | Pass | Fail | Error | Pass Rate |
|-----------|------:|-----:|-----:|------:|----------:|
| spark-authoring+consumption | 2 | 2 | 0 | 0 | 100% |
| sqldw-authoring+consumption | 3 | 3 | 0 | 0 | 100% |
| eventhouse-authoring+consumption | 2 | 2 | 0 | 0 | 100% |
| powerbi-authoring+consumption | 9 | 9 | 0 | 0 | 100% |
| e2e-medallion-architecture | 2 | 2 | 0 | 0 | 100% |

---

## 3. Persistent Failures

All three baseline failures have been **resolved** in the current run:

| Case | Skill | Baseline Status | Current Status | Resolution |
|------|-------|----------------|----------------|------------|
| SA-04 | spark-authoring-cli | FAIL — `CREATE SCHEMA` not supported on Starter Pool | PASS — Schemas created via Livy statement | Fixed — FabricCLITest workspace supports schema operations |
| DWA-10 | sqldw-authoring-cli | FAIL — `FOR TIMESTAMP AS OF` syntax error | PASS (DWA-07) — Time travel query executed with `OPTION (FOR TIMESTAMP AS OF)` | Fixed — correct syntax used |
| DWA-11 | sqldw-authoring-cli | FAIL — Transaction scope mismatch in pooled connection | PASS (DWA-08) — Transaction rolled back, data unchanged | Fixed — SQL file execution avoids pool scope issue |

**Persistent failures: 0** — No test that failed in the baseline also fails in the current run.

### New Errors (current run only)

| Case | Skill | Status | Root Cause |
|------|-------|--------|------------|
| KA-04 | eventhouse-authoring-cli | ERROR (EVAL-BAIL-001) | No blob storage path configured — same underlying issue as baseline SKIP, now categorized as ERROR |

> KA-04 was SKIP in baseline, ERROR in current — the underlying infrastructure gap is unchanged; only the categorization differs. This does not constitute a regression.

---

## 4. New Coverage

Tests that exist in the current run but not in the baseline:

| Category | Tests | Pass | Fail | Error | Details |
|----------|------:|-----:|-----:|------:|---------|
| powerbi-authoring-cli (individual) | 5 | 5 | 0 | 0 | Create/download/datasources/delete Direct Lake semantic model + ambiguous prompt |
| powerbi-consumption-cli (individual) | 8 | 8 | 0 | 0 | Metadata discovery (tables, columns, measures, relationships, scope) + DAX data query + ambiguous prompt |
| spark-authoring+consumption (combined) | 2 | 2 | 0 | 0 | Write->read consistency via Livy session (Delta table) |
| sqldw-authoring+consumption (combined) | 3 | 3 | 0 | 0 | T-SQL write->read consistency + cross-engine PySpark JDBC read |
| eventhouse-authoring+consumption (combined) | 2 | 2 | 0 | 0 | KQL write->read consistency (inline ingest -> query) |
| powerbi-authoring+consumption (combined) | 9 | 9 | 0 | 0 | DirectQuery model with calc groups, UDFs, RLS, relationships + DAX validation + cleanup |
| e2e-medallion-architecture (combined) | 2 | 2 | 0 | 0 | Medallion architecture design + per-layer Spark configuration |
| **Total new** | **31** | **31** | **0** | **0** | |

Additionally, 17 previously skipped tests are now either executed (passing), reclassified as errors, or removed from the suite — zero skips remain.

---

## 5. Improvements

Three tests that were **failing** in the baseline are now **passing**:

| Case | Skill | Baseline Issue | Current Resolution |
|------|-------|---------------|-------------------|
| SA-04 | spark-authoring-cli | `CREATE SCHEMA` fails on Starter Pool | FabricCLITest workspace supports lakehouse schemas |
| DWA-10 to DWA-07 | sqldw-authoring-cli | `FOR TIMESTAMP AS OF` syntax not supported | Correct time-travel syntax used with `OPTION` clause |
| DWA-11 to DWA-08 | sqldw-authoring-cli | Transaction scope mismatch | SQL file-based execution avoids connection pool scope issue |

Skips eliminated: All 17 baseline skips are resolved — infrastructure tests (COPY INTO, MERGE, export, lakehouse SQL EP) now execute; routing/negative tests now verify agent clarification behavior.

## 6. Regressions

**None.** No test that was passing in the baseline is now failing or erroring.

> The single new ERROR (KA-04) does not constitute a regression: it was already non-executing (SKIP) in baseline with the same infrastructure gap (no blob storage path).

---

## Summary

| Category | Count |
|----------|------:|
| New tests added | 31 |
| Fixed (was FAIL, now PASS) | 3 |
| Regressions (was PASS, now FAIL/ERROR) | 0 |
| New errors (infrastructure) | 1 |
| Skips eliminated | 17 |
| Tests removed (check-updates) | 5 |
