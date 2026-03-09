# Eval Plan: powerbi-authoring-cli

## Skill Overview
- **Skill:** `powerbi-authoring-cli`
- **Category:** Power BI Semantic Model Authoring (Write)
- **Purpose:** Create, manage, and deploy Fabric Power BI semantic models via `az rest` CLI against Fabric and Power BI REST APIs — covers TMDL-based create/get/delete, refresh, data sources, and deployment pipelines

## Pre-requisites
- Fabric workspace with capacity assigned (semantic model target) — uses `EVAL_WORKSPACE` from Phase 0
- Authentication configured (`az login`)
- Lakehouse `eval_sales_lakehouse` pre-exists in workspace `FabricCLI-PowerBI-Tests` with Delta tables `sales_transactions` (100 rows) and `products` (5 rows)
- the eval_sales_directlake semantic model, if pre-existing, needs to be deleted

> **Execution Rules:** See [00-overview.md](../00-overview.md#execution-rules-mandatory) — all rules apply to every test below.

## Test Cases

### PBA-01: Create Semantic Models (3 subagents — Direct Lake, DirectQuery, Import)
- **Prompt:**
  "Create or replace 1 semantic models in my workspace connected to lakehouse eval_sales_lakehouse in workspace FabricCLI-PowerBI-Tests using DirectLake, called eval_sales_directlake
  Each model includes:
  - Tables: (1) SalesTransactions — maps to Delta table sales_transactions, columns: transaction_id (int64, key), customer_id (int64), product_id (int64), product_name (string), category (string), quantity (int64), unit_price (decimal), total_amount (decimal), transaction_date (dateTime), region (string). Measures: 'Total Revenue' = SUM(SalesTransactions[total_amount]) format $#,##0.00, 'Average Price' = AVERAGE(SalesTransactions[unit_price]) format $#,##0.00. (2) Products — maps to Delta table products, columns: product_id (int64, key), product_name (string), category (string), base_price (decimal).
  - Relationship: SalesTransactions[product_id] → Products[product_id], many-to-one, single cross-filter direction."
- **Expected:** Semantic models created via TMDL definitions — eval_sales_directlake (EntityPartitionSource, mode: directLake)
- **Pass criteria:** `GET /v1/workspaces/{id}/semanticModels` lists the model; all LROs completed successfully

### PBA-02: Get/Download Semantic Model Definition
- **Prompt:** "Download the TMDL definition of eval_sales_directlake"
- **Expected:** Skill calls `POST .../getDefinition?format=TMDL`, polls LRO if 202, and decodes all definition parts
- **Pass criteria:** Output contains decoded definition.pbism, database.tmdl, model.tmdl, expressions.tmdl (with lakehouse OneLake path), tables/SalesTransactions.tmdl, tables/Products.tmdl


### PBA-03: List Data Sources
- **Prompt:** "List the data sources for eval_sales_directlake"
- **Expected:** Skill calls GET datasources endpoint with Power BI API audience for each model
- **Pass criteria:** The semantic model shows the data source type:
  - **eval_sales_directlake** — Type: AzureDataLakeStorage, Server: onelake.dfs.fabric.microsoft.com, Database/Path: OneLake lakehouse path (connects directly to Delta tables)

### PBA-04: Delete Semantic Models
- **Prompt:** "Delete eval_sales_directlake"
- **Expected:** Skill calls DELETE on the semantic models
- **Pass criteria:** `GET /v1/workspaces/{id}/semanticModels` no longer lists the eval_sales_directlake model

### PBA-05: Negative — Ambiguous Prompt
- **Prompt:** "Update my Power BI model"
- **Expected:** Skill asks for clarification — which workspace, which model, what changes
- **Pass criteria:** Agent does not fail silently or make assumptions; asks the user for missing details

## Write Operations (for consistency pairing)

| Write Case | Object | Type | Paired Read Skill |
|-----------|--------|------|-------------------|
| PBA-01a | eval_sales_directlake (SalesTransactions + Products tables, relationship, measures — Direct Lake to eval_sales_lakehouse in FabricCLI-PowerBI-Tests) | SemanticModel | powerbi-consumption-cli |

## Expected Token Range
- 1500–4000 tokens per invocation
