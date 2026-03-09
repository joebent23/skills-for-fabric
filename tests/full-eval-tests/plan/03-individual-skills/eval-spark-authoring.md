# Eval Plan: spark-authoring-cli

## Skill Overview
- **Skill:** `spark-authoring-cli`
- **Category:** Spark / Data Engineering (Write)
- **Purpose:** Manage Fabric workspaces, develop notebooks, create lakehouses, design pipelines, provision infrastructure

## Pre-requisites
- Active Fabric workspace with Spark capacity
- Fabric API authentication configured
- Eval datasets generated per `01-data-generation.md`

> **Execution Rules:** See [00-overview.md](../00-overview.md#execution-rules-mandatory) — all rules apply to every test below.

## Test Case Types

Tests are split into two categories to keep the eval fast:

- **Description tests** — invoke the skill and verify the text/plan output only. No real Fabric API calls required. Pass/fail based on content of skill response.
- **Infrastructure tests** — invoke the skill and verify real Fabric API state (workspace, lakehouse, table, notebook, session exists and has correct data).

> **Important:** For description tests, do NOT create workspaces, lakehouses, notebooks, or run Spark jobs. Just invoke the skill prompt and evaluate the response text.

## Test Cases

### SA-01: Create a Lakehouse *(infrastructure)*
- **Prompt:** "Create a new lakehouse called eval_sales_lh in my workspace with support for schemas"
- **Expected:** Lakehouse `eval_sales_lh` created via Fabric API
- **Pass criteria:** Lakehouse exists and is accessible
- **Metrics:** Success rate, token usage

### SA-02: Create a Notebook *(infrastructure)*
- **Prompt:** "Create a PySpark notebook that reads a CSV from Files/sales_transactions.csv and writes it as a Delta table called sales_transactions in the lakehouse eval_sales_lh"
- **Expected:** Notebook created with correct PySpark code
- **Pass criteria:** Notebook artifact exists (list items); confirm `updateDefinition` returned `Succeeded` — do NOT call `getDefinition` to re-verify
- **Metrics:** Success rate, token usage

### SA-03: Create a Livy Session *(infrastructure)*
- **Prompt:** "Create a Livy session against lakehouse eval_sales_lh using Starter Pool with Medium compute (driverMemory 56g, driverCores 8, executorMemory 56g, executorCores 8)"
- **Expected:** Livy session started and session ID returned
- **Pass criteria:** Session ID returned, session state is "idle" or "busy"
- **Body format:** Flat JSON with `name`, `driverMemory`, `driverCores`, `executorMemory`, `executorCores` — NOT wrapped in `{"payload": ...}`

### SA-04: Organize Lakehouse Tables *(infrastructure)*
- **Prompt:** "Organize the tables in eval_sales_lh into schemas: raw for ingested data, curated for cleaned data"
- **Expected:** Schema organization applied
- **Pass criteria:** Skill executes without error

### SA-06: Spark Configuration *(description)*
- **Prompt:** "In all notebooks and livy jobs you are creating for the rest of spark authoring tests, as well as in any active livy session, set Spark configuration for eval_sales_lh: spark.sql.shuffle.partitions=8, spark.executor.memory=56g and spark.executor.cores=8"
- **Expected:** Skill describes the correct configuration to apply
- **Pass criteria:** Response includes all 3 correct key=value pairs (`spark.sql.shuffle.partitions=8`, `spark.executor.memory=56g`, `spark.executor.cores=8`) and notes the 56g/8-core Medium tier pairing
- **Note:** Memory value 56g matches Medium compute tier (8 cores = 56g). Do not mix 28g with 8 cores — that is the Small tier (4 cores).
- **Verification:** Text response only — do NOT create sessions or modify notebooks

### SA-07: Delta Lake Table Creation via Spark *(infrastructure)*
- **Prompt:** "Using PySpark, create a Delta table called products with columns: product_id INT, product_name STRING, category STRING, base_price DECIMAL(10,2) in lakehouse eval_sales_lh"
- **Expected:** Delta table created with correct schema
- **Pass criteria:** Table exists with exact column names and types

### SA-08: Write Known Data for Consistency Testing *(infrastructure)*
- **Prompt:** "Write the following 5 rows to the products table in eval_sales_lh: (1,'Product_001','Electronics',9.99), (2,'Product_002','Clothing',19.98), (3,'Product_003','Food',29.97), (4,'Product_004','Home',39.96), (5,'Product_005','Sports',49.95)"
- **Expected:** 5 rows inserted
- **Pass criteria:** Row count = 5 (verified later by consumption skill)
- **Golden data:** See `evalsets/expected-results/products_5rows.json`

### SA-09: Bulk Data Load *(infrastructure)*
- **Pre-step:** Upload `evalsets/data-generation/sales_transactions_100.csv` to `Files/sales_transactions_100.csv` in `eval_sales_lh` (via OneLake API or Fabric upload)
- **Prompt:** "I uploaded a CSV file at Files/sales_transactions_100.csv in eval_sales_lh. Load it into a Delta table called sales_transactions. It has 100 rows of sales data with columns like transaction_id, customer_id, product info, categories, quantities, prices, dates, and regions."
- **Expected:** 100 rows loaded into Delta table with all specified columns
- **Pass criteria:** Table exists with 100 rows, has all 10 columns including `region`
- **Schema verification:** Must have columns: transaction_id (INT), customer_id (INT), product_id (INT), product_name (STRING), category (STRING), quantity (INT), unit_price (DECIMAL), total_amount (DECIMAL), transaction_date (DATE), region (STRING)
- **Golden data:** See `evalsets/expected-results/sales_100_golden.json`

### SA-10: Negative — Ambiguous prompt *(description)*
- **Prompt:** "Set up my data"
- **Expected:** Skill should ask for clarification or provide guidance, not fail silently
- **Pass criteria:** Agent asks clarifying questions or provides structured options
- **Verification:** Text response only — do NOT create any resources

## Write Operations (for consistency pairing)

| Write Case | Table | Rows | Paired Read Skill |
|-----------|-------|------|-------------------|
| SA-08 | products | 5 | spark-consumption-cli |
| SA-09 | sales_transactions | 100 | spark-consumption-cli |

## Expected Token Range
- 1500–4000 tokens per invocation
