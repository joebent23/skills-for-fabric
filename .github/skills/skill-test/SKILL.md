---
name: skill-test
description: >
  Manage the skills-for-fabric evaluation framework: add eval plans for new or existing skills,
  list available tests and their results, generate eval datasets, review metrics, and check
  test coverage. Directs test execution to the tests/ folder. Triggers: "add tests",
  "add evals", "list tests", "show eval results", "run tests", "generate eval data",
  "eval metrics", "test coverage", "missing tests". "show tests"
---

# Skill Test — skills-for-fabric Evaluation Framework

Manage the end-to-end evaluation framework for skills-for-fabric. This skill routes requests to the correct workflow based on user intent — adding tests, listing tests, running tests, viewing results, generating data, or checking coverage.

## When to Use

- When a contributor wants to add evaluation test cases for a new or existing skill
- When someone asks to see what tests exist or what results look like
- When a user wants to run the test suite
- When reviewing eval metrics or checking which skills lack test coverage

## Intent Routing

Parse the user request and route to the appropriate workflow:

| User Intent | Trigger Phrases | Action |
|-------------|----------------|--------|
| **Add evals** | "add tests", "add evals", "add evals for missing skills", "create eval plan" | → [Workflow: Add Evals](#workflow-add-evals) |
| **List tests** | "list tests", "list evals", "show me the list of tests", "what tests exist", "show eval plans" | → [Workflow: List Tests](#workflow-list-tests) |
| **Run tests** | "run tests", "run evals", "execute tests", "run the eval suite" | → [Workflow: Run Tests](#workflow-run-tests) |
| **View results** | "show eval results", "test results", "eval results", "executive summary" | → [Workflow: View Results](#workflow-view-results) |
| **Generate data** | "generate eval data", "generate test data", "create eval datasets" | → [Workflow: Generate Data](#workflow-generate-data) |
| **View metrics** | "eval metrics", "test metrics", "what metrics", "how are tests scored" | → [Workflow: View Metrics](#workflow-view-metrics) |
| **Check coverage** | "test coverage", "which skills have tests", "missing tests", "skills without evals" | → [Workflow: Check Coverage](#workflow-check-coverage) |

---

## Workflow: Add Evals

Follow the instructions in `tests/full-eval-tests/README.md` § "Adding Evals for New Skills".

### Automated Path (Recommended)

Give the agent the prompt:

```
Add evals for the missing skills
```

The agent will:
1. Detect missing skills by comparing installed skills against existing eval plans in `tests/full-eval-tests/plan/03-individual-skills/`
2. Generate individual eval plans (`plan/03-individual-skills/eval-<skill-name>.md`) with 10–12 test cases
3. Generate combined eval plans (`plan/04-combined-skills/eval-<skill>-authoring-plus-consumption.md`)
4. Create golden data in `tests/full-eval-tests/evalsets/expected-results/`
5. Update tracking files: `plan/00-overview.md`, `README.md`, `plan/04-combined-skills/eval-full-pipeline.md`

### Manual Path

To add evals for a specific skill `<new-skill>`:

1. Create `tests/full-eval-tests/plan/03-individual-skills/eval-<new-skill>.md` using the template in the README
2. Each test case needs: Case ID (unique prefix), Prompt, Expected result, Pass criteria, at least one negative/ambiguous test
3. If the skill has an authoring+consumption pair, create `tests/full-eval-tests/plan/04-combined-skills/eval-<new-skill>-authoring-plus-consumption.md`
4. Add golden data to `tests/full-eval-tests/evalsets/expected-results/`
5. Update `plan/00-overview.md`, `README.md` directory tree, and `plan/04-combined-skills/eval-full-pipeline.md`

### Eval Plan Template

Use the template from `tests/full-eval-tests/README.md` § "Eval Plan Template". Every eval plan must include:
- Skill overview (name, category, R/W, purpose)
- Pre-requisites
- Numbered test cases (XX-01 through XX-10+) with Prompt / Expected / Pass criteria
- At least one negative/ambiguous test case as the last case
- Write Operations table (if the skill writes data)
- Expected Token Range

---

## Workflow: List Tests

Show the user what eval plans and test cases exist.

### Individual Skill Evals

List files in `tests/full-eval-tests/plan/03-individual-skills/`:

```bash
ls tests/full-eval-tests/plan/03-individual-skills/
```

### Combined Skill Evals

List files in `tests/full-eval-tests/plan/04-combined-skills/`:

```bash
ls tests/full-eval-tests/plan/04-combined-skills/
```

### Quick Tests (tests.json)

Show the test cases defined in `tests/tests.json` — these are the prompt-based tests run by the test runner.

### Recommended Execution Order

| Order | Eval Plan | Reason |
|-------|-----------|--------|
| 1 | eval-check-updates.md | Verify skills are installed |
| 2 | eval-spark-authoring.md | Create lakehouses and load data |
| 3 | eval-sqldw-authoring.md | Create warehouse tables and load data |
| 4 | eval-eventhouse-authoring.md | Create Eventhouse tables and ingest data |
| 5 | eval-spark-consumption.md | Read back lakehouse data |
| 6 | eval-sqldw-consumption.md | Read back warehouse data |
| 7 | eval-eventhouse-consumption.md | Read back Eventhouse data |
| 8 | eval-medallion.md | End-to-end medallion pipeline |

---

## Workflow: Run Tests

> **⛔ DO NOT execute tests from this skill.** The agent must NEVER run `copilot`, `run-full-tests.ps1`, or any eval prompt directly. Instead, tell the user the exact commands to run manually.

When the user asks to run tests, respond **only** with instructions. Do not execute any commands. Tell the user:

1. Open a terminal and navigate to the `tests/` directory at the repository root:
   ```powershell
   cd tests
   ```

2. Run the full test suite:
   ```powershell
   .\run-full-tests.ps1
   ```

3. To specify an output directory:
   ```powershell
   .\run-full-tests.ps1 -TestFolder C:\temp\eval-run-01
   ```

### Important

- **The agent must NEVER run tests itself** — only provide the user with instructions
- **Tests must be run by the user** from inside the `tests/` folder
- The script copies the eval framework to a working folder and launches copilot there

---

## Workflow: View Results

Show the user existing evaluation results.

### Detailed Results

Read `tests/full-eval-tests/eval-results.md` — contains per-skill, per-test-case pass/fail with notes, consistency test results, failure analysis, and skip reasons.

### Executive Summary

Read `tests/full-eval-tests/executive-summary.md` — contains the high-level summary: overall pass rate, results by skill, data consistency scores, failure analysis, and recommendations.

### Key Metrics from Latest Run

| Metric | Value |
|--------|-------|
| Overall pass rate | 94.7% (54/57 executed) |
| Write/Read consistency | 100% (5/5 exact matches) |
| Total test cases | 74 |
| Skipped | 17 |

---

## Workflow: Generate Data

Generate synthetic evaluation datasets using the specifications in `tests/full-eval-tests/plan/01-data-generation.md`.

### Using the Generation Script

```bash
python tests/full-eval-tests/evalsets/data-generation/generate.py
```

### Datasets

| Dataset | Rows | Format | Used By |
|---------|------|--------|---------|
| sales_transactions | 100 / 1K / 10K | CSV | SQL DW, Spark |
| customers | 100 | CSV | Join testing |
| products | 50 | CSV | Join testing |
| sensor_readings | 500 | JSON | Spark semi-structured |

### Golden Results

Pre-computed expected results are in `tests/full-eval-tests/evalsets/expected-results/` and are used to verify consistency.

---

## Workflow: View Metrics

Explain the evaluation metrics defined in `tests/full-eval-tests/plan/02-metrics.md`.

| Metric | Definition |
|--------|-----------|
| **Success Rate** | `passed / total × 100` — whether the skill executed correctly |
| **Token Usage** | Input + output tokens consumed per eval prompt |
| **Read/Write Consistency** | Data written by authoring skill must be exactly retrievable by consumption skill |

### Grading

| Grade | Criteria |
|-------|----------|
| PASS | Skill invoked correctly, output matches expected |
| FAIL_INVOCATION | Wrong skill invoked or not invoked |
| FAIL_EXECUTION | Skill invoked but errored |
| FAIL_RESULT | Skill completed but output mismatches |

### Pass Thresholds

| Metric | Threshold |
|--------|-----------|
| Success Rate | ≥ 90% per skill |
| Token Usage | Within 2× of baseline |
| Read/Write Consistency | 100% exact match |

---

## Workflow: Check Coverage

Compare installed skills against existing eval plans to identify gaps.

### Steps

1. List all skills from the marketplace/plugin:
   ```
   check-updates, spark-authoring-cli, spark-consumption-cli, sqldw-authoring-cli,
   sqldw-consumption-cli, eventhouse-authoring-cli, eventhouse-consumption-cli, e2e-medallion-architecture
   ```

2. List existing individual eval plans:
   ```bash
   ls tests/full-eval-tests/plan/03-individual-skills/
   ```

3. Compare and report which skills have eval coverage and which are missing.

4. For missing skills, suggest running the [Add Evals](#workflow-add-evals) workflow.

---

## Must

- **NEVER execute tests, eval prompts, or the test runner script** — only provide instructions for the user to run manually
- **Always route "run tests" to the `tests/` folder** — tell the user to navigate there and run `run-full-tests.ps1`
- **Follow the eval plan template** when creating new eval plans — every test case needs Case ID, Prompt, Expected, Pass criteria
- **Include at least one negative/ambiguous test** in every new eval plan
- **Update tracking files** when adding evals — `plan/00-overview.md`, `README.md`, `eval-full-pipeline.md`
- **Reference golden data** in `evalsets/expected-results/` for consistency tests

## Prefer

- Automated eval generation ("add evals for missing skills") over manual creation
- Reading existing eval plans as templates before creating new ones
- Running the full suite rather than individual tests for comprehensive coverage
- Checking the executive summary before diving into detailed results

## Avoid

- Running eval prompts outside the `tests/` directory
- **Executing tests, copilot commands, or the run-full-tests.ps1 script** — the agent must only tell the user how to run them
- Creating eval plans without a negative/ambiguous test case
- Duplicating content already in the README or plan documents — reference them instead
- Modifying golden result files unless the underlying data generation rules change
- Skipping the tracking file updates when adding new evals

## Examples

### Adding Tests

**User:** "Add tests for the powerbi-consumption-cli skill"

**Agent:** Creates `tests/full-eval-tests/plan/03-individual-skills/eval-powerbi-consumption.md` with 10–12 test cases following the template, adds golden data to `evalsets/expected-results/`, and updates tracking files.

### Listing Tests

**User:** "What tests exist?"

**Agent:** Lists all eval plans in `plan/03-individual-skills/` and `plan/04-combined-skills/`, plus the quick tests in `tests/tests.json`, with the recommended execution order.

### Running Tests

**User:** "Run the tests"

**Agent:**
> Tests must be run from the `tests/` folder. Navigate there and execute:
> ```powershell
> cd tests
> .\run-full-tests.ps1
> ```

### Viewing Results

**User:** "Show me the eval results"

**Agent:** Reads `tests/full-eval-tests/eval-results.md` and presents the summary table, highlighting pass rates and any failures.
