# skills-for-fabric Evaluation Framework

Machine-facing evaluation guidance for the Copilot CLI agent. This README defines eval content and conventions inside `full-eval-tests/`.

## Structure

```
full-eval-tests/
+-- README.md                          # This file
+-- eval-results.md                    # Detailed evaluation results (latest run)
+-- executive-summary.md               # Executive summary of latest eval run
+-- plan/
|   +-- 00-overview.md                 # Master evaluation plan
|   +-- 01-data-generation.md          # How to generate eval datasets
|   +-- 02-metrics.md                  # Metric definitions and collection
|   +-- 03-individual-skills/          # Per-skill eval plans
|   |   +-- eval-spark-authoring.md
|   |   +-- eval-spark-consumption.md
|   |   +-- eval-sqldw-authoring.md
|   |   +-- eval-sqldw-consumption.md
|   |   +-- eval-eventhouse-authoring.md
|   |   +-- eval-eventhouse-consumption.md
|   |   +-- eval-powerbi-authoring.md
|   |   +-- eval-powerbi-consumption.md
|   |   +-- eval-medallion.md
|   +-- 04-combined-skills/            # Multi-skill eval plans
|       +-- eval-spark-authoring-plus-consumption.md
|       +-- eval-sqldw-authoring-plus-consumption.md
|       +-- eval-eventhouse-authoring-plus-consumption.md
|       +-- eval-powerbi-authoring-plus-consumption.md
|       +-- eval-full-pipeline.md.TOO_LONG_TO_RUN
+-- evalsets/
|   +-- data-generation/               # Pre-generated test data (CSV/JSON)
|   |   +-- generate.py                # Regenerates all data files deterministically
|   |   +-- sales_transactions_100.csv
|   |   +-- sales_transactions_1000.csv
|   |   +-- sales_transactions_10000.csv
|   |   +-- customers.csv
|   |   +-- products.csv
|   |   +-- sensor_readings.json
|   +-- expected-results/              # Golden results for consistency checks
|       +-- consistency_3rows.json
|       +-- products_5rows.json
|       +-- sales_100_golden.json
|       +-- sales_5rows.json
|       +-- semantic_model_eval_sales.json
|       +-- sensor_5rows.json
+-- result/                            # Checked-in eval result markdown files
    +-- eval-results.md                # Merged summary from individual results
    +-- regression_analysis.md         # Baseline vs current comparison
```

## Execution Context

- This folder is copied to a temporary execution directory by the test runner.
- Instructions here are for eval interpretation and execution behavior inside the copied folder.
- Script/operator usage instructions belong outside this folder (for example, in `tests/README.md` and `.github/skills/skill-test/SKILL.md`).
- Workspace cleanup and execution rules are canonical in `plan/00-overview.md` and must be followed exactly.

## Metrics

| Metric | Description |
|--------|-------------|
| **Success Rate** | Whether the skill executed correctly (pass/fail per test case) |
| **Token Usage** | Input + output tokens consumed per eval run |
| **Read/Write Consistency** | Data written via one skill must be exactly retrievable via read skills |

## Eval Flow

### Manual/Runner Phases

Follow the phases in [plan/00-overview.md](plan/00-overview.md):

### Step 0: Select Workspace & Clean

Before running any tests, select the target workspace and clean all existing items:

1. **Workspace Selection:** If no workspace is specified, ask for the workspace name. Default: `FabricCLITest`.
2. **Workspace Cleanup:** Delete **ALL items** in the selected workspace to ensure a clean slate. The workspace itself is preserved.

**Cleanup procedure:**
```
1. Resolve workspace name to ID:
   GET https://api.fabric.microsoft.com/v1/workspaces?$filter=displayName eq '{EVAL_WORKSPACE}'

2. List all items:
   GET https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items

3. Delete each item (lakehouses, warehouses, eventhouses, notebooks, pipelines,
   Spark job definitions, KQL databases, semantic models, reports, etc.):
   DELETE https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{itemId}

4. Verify empty:
   GET https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items
   → Expected: empty list
```

> **⚠️ WARNING:** This permanently deletes all items in the workspace. Ensure the correct workspace is selected.

1. **Phase 0** — Select workspace and clean all items
2. **Phase 1** — Use checked-in deterministic data in `evalsets/data-generation/` (regenerate only when intentionally refreshing fixtures)
3. **Phase 2** — Run individual skill evals (plans in `plan/03-individual-skills/`)
4. **Phase 3** — Run combined skill evals (plans in `plan/04-combined-skills/`)
5. **Phase 4** — Collect metrics per `plan/02-metrics.md`

> **Execution rules, result file format, and regression analysis** are all specified in [plan/00-overview.md](plan/00-overview.md). Follow them regardless of whether you run manually or via the script.

## Adding Evals for New Skills

When a new FabricSkill is added to the marketplace, you can automatically generate its eval plan, combined eval, golden data, and update all tracking files by giving the Copilot CLI agent a single prompt:

```
Add evals for the missing skills
```

The agent will:

1. **Detect missing skills**  --  compare the installed skills list against existing eval plans in `plan/03-individual-skills/`
2. **Generate individual eval plans**  --  create `plan/03-individual-skills/eval-<skill-name>.md` with 10-12 test cases following the established pattern (schema, CRUD, policies, negative tests)
3. **Generate combined eval plans**  --  create `plan/04-combined-skills/eval-<skill>-authoring-plus-consumption.md` with write->read consistency tests
4. **Create golden data**  --  add expected results to `evalsets/expected-results/` for consistency verification
5. **Update existing files**  --  patch `plan/00-overview.md` (skills table), `README.md` (directory tree)
<!-- and `plan/04-combined-skills/eval-full-pipeline.md` (add steps for the new skill) -->

### Manual Steps (if you prefer)

To add evals for a skill called `<new-skill>` by hand:

1. **Create the individual eval plan:**
   ```
   plan/03-individual-skills/eval-<new-skill>.md
   ```
   Use any existing eval plan as a template. Each test case needs:
   - **Case ID**  --  prefix with a unique 2-3 letter code (e.g., `NS-01`)
   - **Prompt**  --  the exact text to send to the agent
   - **Expected result**  --  what the skill should produce
   - **Pass criteria**  --  how to verify success
   - At least one **negative/ambiguous test** (last case)
   - A **Write Operations** table if the skill writes data

2. **Create the combined eval plan** (if the skill has an authoring+consumption pair):
   ```
   plan/04-combined-skills/eval-<new-skill>-authoring-plus-consumption.md
   ```
   Include 1 test to author using the skill
   Include 1 test to consume the content in the previous step with **each skill which has consumption**, including the one used for authoring.

3. **Add golden data** to `evalsets/expected-results/` for any known-data insert tests.

4. **Update tracking files:**
   - `plan/00-overview.md`  --  add a row to the Skills Under Test table
   - `README.md`  --  add the new files to the directory tree
<!--   - `plan/04-combined-skills/eval-full-pipeline.md`  --  add steps for the new skill -->

5. **Run the evals:**
   ```
   Run all the evals and output the result in a .md file
   ```

### Eval Plan Template

```markdown
# Eval Plan: <skill-name>

## Skill Overview
- **Skill:** `<skill-name>`
- **Category:** <category> (<Read|Write|Read+Write>)
- **Purpose:** <one-line description>

## Pre-requisites
- <required Fabric resources>
- Eval datasets generated per `01-data-generation.md`

## Test Cases

### XX-01: <Title>
- **Prompt:** "<exact prompt>"
- **Expected:** <what should happen>
- **Pass criteria:** <how to verify>

### XX-10: Negative  --  Ambiguous prompt
- **Prompt:** "<vague prompt>"
- **Expected:** Skill asks for clarification
- **Pass criteria:** Agent does not fail silently

## Write Operations (for consistency pairing)

| Write Case | Table | Rows | Paired Read Skill |
|-----------|-------|------|-------------------|

## Expected Token Range
- <min>-<max> tokens per invocation
```
