# Eval Plan: spark-consumption-cli

## Skill Overview
- **Skill:** `spark-consumption-cli`
- **Category:** Spark / Analytics (Read)
- **Purpose:** Analyze lakehouse data via Livy sessions, PySpark/Spark SQL, DataFrames

## Pre-requisites
- Lakehouse `eval_sales_lh` with tables populated by `spark-authoring-cli` evals
- Livy session available or will be created by skill
- Eval datasets loaded: `sales_transactions` (100 rows)

> **Execution Rules:** See [00-overview.md](../00-overview.md#execution-rules-mandatory) — all rules apply to every test below.

## Phase 0: Data Prerequisites

Before running the test cases below, the evaluating agent **MUST** verify and create all prerequisite data in `eval_sales_lh`. These tables may or may not exist from a prior spark-authoring eval. The agent should check each one and create any that are missing.

> **Data source:** All pre-generated data files are in `evalsets/data-generation/`. Use those files instead of generating data inline. The files are produced by `evalsets/data-generation/generate.py` and match the spec in `plan/01-data-generation.md`.

### 0a: Verify `sales_transactions` schema

Check that `sales_transactions` exists with a `region` column and 100 rows. If the table is missing, has the wrong schema, or has the wrong row count:

1. Upload `evalsets/data-generation/sales_transactions_100.csv` to `Files/sales_transactions_100.csv` in `eval_sales_lh`
2. Load it into a Delta table called `sales_transactions` using PySpark (read CSV with header, infer schema, overwrite the table)

Expected schema: `transaction_id INT, customer_id INT, product_id INT, product_name STRING, category STRING, quantity INT, unit_price DECIMAL(10,2), total_amount DECIMAL(10,2), transaction_date DATE, region STRING`


## Test Cases

### SC-01: Simple Row Count
- **Prompt:** "Using PySpark, count the rows in the sales_transactions table in eval_sales_lh"
- **Expected result:** 100
- **Pass criteria:** Exact match to expected row count

### SC-02: Filtered Query
- **Prompt:** "Using Spark SQL, find all sales transactions in the Electronics category from eval_sales_lh"
- **Expected result:** 20 rows (for 100-row dataset, every 5th row)
- **Pass criteria:** Row count = 20, all rows have category = "Electronics"

### SC-03: Aggregation
- **Prompt:** "Using PySpark DataFrames, calculate total sales amount per region from sales_transactions in eval_sales_lh"
- **Expected result:** 4 rows (East, West, North, South), amounts match golden results
- **Pass criteria:** 4 regions, amounts match pre-computed values


## Consistency Test Matrix

| Read Case | Write Case | Table | Verification |
|-----------|-----------|-------|-------------|
| SC-01 | SA-09 or Phase 0a | sales_transactions | Row count = 100 |
| SC-02 | SA-09 or Phase 0a | sales_transactions | Electronics count = 20 (deterministic: rows where i%5==0) |
| SC-03 | SA-09 or Phase 0a | sales_transactions | 4 regions: East(25), West(25), North(25), South(25) |

## Expected Token Range
- 1500–3500 tokens per invocation
