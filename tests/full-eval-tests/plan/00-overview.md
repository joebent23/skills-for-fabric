# Master Evaluation Plan

## Objective

Evaluate all 10 skills-for-fabric for correctness, efficiency, and data consistency. Each skill is tested individually, then in combination with other skills to verify end-to-end workflows.

## Skills Under Test

| ID | Skill | Category | R/W | Has Eval Plan |
|----|-------|----------|-----|---------------|
| S2 | `spark-authoring-cli` | Spark Authoring | Write | Yes |
| S3 | `spark-consumption-cli` | Spark Consumption | Read | Yes |
| S4 | `sqldw-authoring-cli` | SQL DW Authoring | Write | Yes |
| S5 | `sqldw-consumption-cli` | SQL DW Consumption | Read | Yes |
| S6 | `e2e-medallion-architecture` | Pipeline | Write+Read | Yes |
| S7 | `eventhouse-authoring-cli` | KQL / Eventhouse Authoring | Write | Yes |
| S8 | `eventhouse-consumption-cli` | KQL / Eventhouse Consumption | Read | Yes |
| S9 | `powerbi-authoring-cli` | Power BI Semantic Model Authoring | Write | Yes |
| S10 | `powerbi-consumption-cli` | Power BI Semantic Model Consumption | Read | Yes |

## Evaluation Phases

### Phase 0: Workspace Selection & Cleanup

Before any tests run, the evaluating agent must:

#### Step 0a: Workspace Selection

If no workspace is specified, **ask the user** for the target Fabric workspace name. 

- **Default value:** `FabricCLITest`
- The selected workspace name is stored as `EVAL_WORKSPACE` and used for all subsequent eval phases.
- All prompts that reference "my workspace" resolve to `EVAL_WORKSPACE`.

**Phase 0 is run-once per session.** If Phase 0 has already completed (workspace ID resolved and cleanup attempted), subsequent eval plans in the same session MUST skip Phase 0 and reuse the previously resolved `EVAL_WORKSPACE` and workspace ID. Do NOT re-resolve the workspace or re-attempt cleanup for each eval plan.

#### Step 0b: Workspace Cleanup — Delete ALL Items

Delete **every item** in the selected workspace to ensure a clean slate. The workspace itself is preserved but fully emptied.

**Cleanup procedure:**
```
1. Resolve EVAL_WORKSPACE to its workspace ID, just like you would do for any Spark job
   
2. List all items in the workspace
   GET https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items

3. Delete each item (lakehouses, warehouses, eventhouses, notebooks, pipelines,
   Spark job definitions, KQL databases, semantic models, reports, and any other items)
   DELETE https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{itemId}

4. Verify the workspace is empty
   GET https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items
   → Expected: empty list
```

> **⚠️ WARNING:** This step permanently deletes all items in the workspace. Ensure the correct workspace is selected.

**Retry limit:** If a DELETE call for an item fails, retry **once**. If it fails again, log the item as `UNDELETABLE` (item ID, type, and error message) and move on to the next item. Do NOT attempt alternative endpoints, different HTTP clients, or workaround strategies — these are wasted tokens.

**Known blockers:** Items with tenant-enforced **sensitivity labels** cannot be deleted via the Fabric REST API. They require manual deletion by a tenant admin or a user with Information Protection permissions. These items should be logged and skipped without further retry.

### Phase 1: Data Preparation
- Use checked-in deterministic datasets from `evalsets/data-generation/`
- Use checked-in golden results from `evalsets/expected-results/`
- Regenerate data only when intentionally refreshing fixtures or when generation rules change
- See `01-data-generation.md`

### Phase 2: Individual Skill Evaluation
- Run each skill through a set of test prompts
- Measure success rate and token usage per prompt
- See `03-individual-skills/eval-*.md`

**Execution order:** Authoring (write) evals MUST run before their corresponding consumption (read) evals. Consumption evals depend on artifacts created by authoring evals.


### Phase 3: Combined Skill Evaluation
- Chain write skills → read skills and verify consistency
- Run multi-step pipeline scenarios
- See `04-combined-skills/eval-*.md`


### Phase 4: Metrics Collection & Reporting
- Aggregate success rates, token counts, consistency scores
- See `02-metrics.md`

### Phase 4a: Runner Execution Summary

After all eval plans run, the runner should print a concise execution summary table to the console/log with one row per plan:

| Column | Meaning |
|--------|---------|
| Plan | Eval plan name (for example, `eval-spark-authoring`) |
| Duration | Runtime in seconds |
| Error | Captured execution error (if any) |

The summary must also include:

1. Total number of plans executed
2. Destination path where result files were copied

This summary is operational logging only. It does not replace the required markdown result files.

## Execution Rules (MANDATORY)

> **These rules are non-negotiable. The eval runner MUST follow them exactly for every eval plan.**

1. **EXECUTE every test case** — Send the prompt to the agent AND verify the actual Fabric API response or output. Every test MUST produce a real API call or command execution.
2. **No shortcuts** — Do NOT mark any test as "documented", "validated", "deferred", or "skipped". Do NOT invent a "tiered execution strategy" or any approach that avoids running tests.
3. **Record actual output** — For each test, capture the real HTTP status code, row counts, data returned, or error message. Synthetic or assumed results are not acceptable.
4. **Continue on failure** — If a test fails, record the failure with the actual error and proceed to the next test. Do not stop the eval.
5. **Sequential dependencies** — Tests that depend on prior write operations MUST be run in order.
6. **100% execution rate required** — The eval is only valid if every test case was actually executed against the Fabric workspace.
7. **No extra files** — Do NOT create any files other than the one result file specified per eval plan. No API reference docs, no execution summaries, no technical documentation — ONLY the results file.
8. **Use skills** — Execute ALL test cases and use skills. The whole purpose of this suite is to test skills
## Bailout Conditions (MANDATORY)

To prevent the evaluator from getting stuck on one test, apply these bailout rules for every case:

1. **No clear rules / insufficient instructions**
   - If the test cannot be executed because required rules or inputs are missing/contradictory, record an error and move on.
   - Use error code: **`EVAL-BAIL-001`**.

2. **Max retry attempts reached**
   - For any single test case, do not retry more than **3 attempts** total (initial attempt + up to 2 retries).
   - for any task which is part of your plan for executing a test case, do not retry more than **3 attempts** total (initial attempt + up to 2 retries).
   - After the 3rd failed attempt, record an error and move to the next test.
   - Use error code: **`EVAL-BAIL-003`**.

3. **Never block plan progress**
   - Bailout on the current test only.
   - Continue with the next test case in the same eval plan.
   - Do not abort the entire plan unless the runner process itself crashes.

4. **Suite-level bailout on skip**
   - If any plan result marks a test as `SKIP`/`SKIPPED`, the runner must abort the full suite immediately.
   - Use error code: **`EVAL-SUITE-010`**.
   - Rationale: skipped tests can invalidate dependency assumptions for subsequent plans.


## Result File Format

Each eval plan produces **exactly one** result file. The file MUST be named `{plan-name}-results.md` where `{plan-name}` matches the eval plan filename without extension (e.g., `eval-spark-authoring.md` → `eval-spark-authoring-results.md`).

### Required structure

```markdown
# Eval Results: {skill or combined name}

**Workspace:** {workspace name} ({workspace ID})
**Run Date:** {YYYY-MM-DD}

## Summary Table

| Test ID | Status | Details |
|---------|--------|---------|
| XX-01   | PASS   | {brief} |
| XX-02   | FAIL   | {brief} |
...

If `Status = ERROR`, include the bailout code in `Details` (for example: `EVAL-BAIL-003: failed after 3 attempts`).

## Detailed Test Results

### XX-01: {Title}
- Prompt sent
- Actual API/command output
- Pass/fail determination
- If errored, include `Error Code` and `Attempt Count`

(repeat for each test case)

## Totals

| Status | Count |
|--------|-------|
| PASS   | N     |
| FAIL   | N     |
| ERROR  | N     |
| Total  | N     |
```

## Merged Summary

After all individual result files are produced, a single merged summary MUST be generated at `result/eval-results.md` containing:

1. A per-skill summary table (Skill | Total | Pass | Fail | Skip | Pass Rate)
2. An Overall row with aggregate counts
3. Detailed results per skill (extracted from individual result files)
4. A Failures Analysis table (only for FAIL cases: Case | Skill | Issue | Root Cause)

> **Important:** The merged summary is generated by *reading* the individual result files — it does NOT re-run any tests.

## Regression Analysis

After the merged summary is produced, compare results against the checked-in baseline at:

```
https://github.com/microsoft/skills-for-fabric/blob/main/tests/full-eval-tests/result/eval-results.md
```

Write the comparison to `result/regression_analysis.md` with:

1. **Overall pass rate** — baseline vs current, delta
2. **Per-skill comparison** — highlight improvements and regressions
3. **Persistent failures** — tests that failed in both runs (same root cause?)
4. **New coverage** — tests that exist in current but not in baseline
5. **Verdict** — one of: `BETTER` (no regressions, pass rate same or higher), `REGRESSION` (any test that was passing is now failing), `SAME` (identical results)

If no baseline exists (first run), skip the comparison.

## Eval Execution Model

Each eval is a **prompt → skill invocation → result verification** loop:

> **Note:** All prompts that reference "my workspace" refer to the `EVAL_WORKSPACE` selected in Phase 0 (default: `FabricCLITest`).

```
For each eval case:
  1. Record start state (token counter, workspace state)
  2. Send the eval prompt to the agent
  3. Agent invokes the skill
  4. Capture: success/failure, token usage, output
  5. For write+read pairs: verify read output == expected data
  6. Log results to eval tracker
```

## Pass/Fail Criteria

| Metric | Pass Threshold |
|--------|---------------|
| Success Rate | ≥ 90% per skill |
| Token Usage | Within 2x of baseline (established in first run) |
| Read/Write Consistency | 100% exact match for all write→read pairs |

## Dependencies

- Active Microsoft Fabric workspace with capacity
- At least one Lakehouse provisioned
- At least one Data Warehouse provisioned
- At least one Eventhouse with a KQL Database provisioned
- At least one Power BI Semantic Model provisioned (for powerbi-authoring/consumption evals)
- Fabric API authentication configured (Azure CLI or token)
