# Eval Plan: sqldw-consumption-cli

## Skill Overview
- **Skill:** `sqldw-consumption-cli`
- **Category:** SQL Data Warehouse (Read)
- **Purpose:** Execute read-only T-SQL queries against Fabric Warehouse, Lakehouse SQL Endpoints, and Mirrored Databases

## Pre-requisites
- Fabric Data Warehouse with `eval.sales_transactions` table populated by `sqldw-authoring-cli` evals
- Lakehouse SQL Endpoint accessible
- Tables: `eval.sales_transactions` (5 or 100 rows), `eval.customers` (optional)

> **Execution Rules:** See [00-overview.md](../00-overview.md#execution-rules-mandatory) — all rules apply to every test below.

## Test Cases

### DWC-01: Simple Row Count
- **Prompt:** "How many rows are in eval.sales_transactions in my warehouse?"
- **Expected result:** 100 (or 5, depending on which write eval ran)
- **Pass criteria:** Exact count match

### DWC-02: SELECT All (Consistency with DWA-03)
- **Prompt:** "Show all rows from eval.sales_transactions in my warehouse ordered by transaction_id"
- **Expected result:** Exact 5 rows matching DWA-03 insert data
- **Pass criteria:**
  - Row count = 5
  - transaction_id: [1, 2, 3, 4, 5]
  - product_name: ["Product_001", "Product_002", "Product_003", "Product_004", "Product_005"]
  - total_amount: [19.98, 59.94, 119.88, 199.80, 299.70]
  - **EXACT MATCH required — this is a consistency test**

### DWC-03: Filtered Query
- **Prompt:** "Query eval.sales_transactions in my warehouse where category = 'Electronics'"
- **Expected result:** Rows with category = Electronics only
- **Pass criteria:** All returned rows have category = 'Electronics'

### DWC-04: JOIN Query
- **Prompt:** "Join eval.sales_transactions with eval.customers on customer_id and show total sales per customer tier in my warehouse"
- **Expected result:** 3 rows (Bronze, Silver, Gold)
- **Pass criteria:** Tier names and totals match

### DWC-05: Export to CSV
- **Prompt:** "Export eval.sales_transactions from my warehouse to CSV"
- **Expected result:** CSV output or file generated
- **Pass criteria:** CSV contains correct headers and row count

### DWC-06: Lakehouse SQL Endpoint Query
- **Prompt:** "Query the sales_transactions table from the lakehouse SQL endpoint of eval_sales_lh"
- **Expected result:** Data returned from lakehouse via SQL
- **Pass criteria:** Row count matches lakehouse data

### DWC-07: Negative — Write attempt should fail/be refused
- **Prompt:** "Delete all rows from eval.sales_transactions in my warehouse"
- **Expected result:** Skill refuses or routes to authoring skill
- **Pass criteria:** No data deleted, user informed this is a read-only skill

## Consistency Test Matrix

| Read Case | Write Case (sqldw-authoring) | Table | Verification |
|-----------|------------------------------|-------|-------------|
| DWC-01 | DWA-04 | eval.sales_transactions | Row count = 100 |
| DWC-02 | DWA-03 | eval.sales_transactions | Cell-level exact match, 5 rows |
| DWC-04 | DWA-03 | eval.sales_transactions | SUM = 699.30 (19.98+59.94+119.88+199.80+299.70) |

## Expected Token Range
- 800–2500 tokens per invocation
