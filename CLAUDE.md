# Microsoft Fabric Development Instructions

> **Update Check**: At session start, check for skills-for-fabric updates by reading the remote `package.json` version from `https://github.com/microsoft/skills-for-fabric` (via `git fetch origin master --quiet && git show origin/master:package.json` or GitHub API with authentication) and comparing with the local `package.json` version. Show changelog if update available.

This project uses Microsoft Fabric for data engineering, warehousing, and analytics.

## Architecture Mode

- Use the hybrid layering model: **Agents → Skills → Common**.
- For cross-workload orchestration, start with `agents/FabricDataEngineer.agent.md`.
- Delegate deep endpoint implementation to relevant skills under `skills/`.

## Authentication

All Fabric operations require Azure AD authentication. For development:

```bash
# Login to Azure
az login

# Get token for Fabric REST API
az account get-access-token --resource https://api.fabric.microsoft.com

# Get token for SQL connections (Warehouse, Lakehouse SQL Endpoint)
az account get-access-token --resource https://database.windows.net
```

## Fabric REST APIs

All Fabric operations use the REST APIs documented at:
https://learn.microsoft.com/en-us/rest/api/fabric/articles/

## Developer vs Consumer Patterns

### Developers
- Use **REST APIs** to create/manage artifacts (workspaces, warehouses, lakehouses)
- Use **protocol-specific** connections to access data:
  - ODBC/JDBC for Warehouse queries
  - Spark/PySpark for Lakehouse data
  - XMLA/DAX for Semantic Models
  - KQL for Real-Time Intelligence

### Consumers
- Use **MCP servers** for natural language queries
- Limited to: Semantic Models, Warehouses, Lakehouse SQL Endpoints
- No ODBC/JDBC setup needed - MCP handles connections

## Workloads

### Data Engineering
- **Lakehouse**: Delta tables, Spark, file management
  - Docs: https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-overview
- **Notebooks**: PySpark notebooks with mssparkutils
  - Docs: https://learn.microsoft.com/en-us/fabric/data-engineering/how-to-use-notebook
- **Spark Jobs**: Production Spark workloads
  - Docs: https://learn.microsoft.com/en-us/fabric/data-engineering/spark-job-definition

### Data Warehouse
- **Warehouse**: T-SQL data warehouse
  - Docs: https://learn.microsoft.com/en-us/fabric/data-warehouse/data-warehousing
  - Note: Limited T-SQL surface area - check supported features

### Data Integration
- **Pipelines**: Orchestration and data movement
  - Docs: https://learn.microsoft.com/en-us/fabric/data-factory/data-factory-overview
- **Dataflows Gen2**: Low-code transformations with Power Query
  - Docs: https://learn.microsoft.com/en-us/fabric/data-factory/dataflows-gen2-overview

### Real-Time Intelligence
- **Eventstreams**: Real-time data ingestion
  - Docs: https://learn.microsoft.com/en-us/fabric/real-time-intelligence/event-streams/overview
- **KQL Database**: Time-series queries with Kusto
  - Docs: https://learn.microsoft.com/en-us/fabric/real-time-intelligence/create-database

### Business Intelligence
- **Semantic Models**: DAX, XMLA, Power BI integration
  - Docs: https://learn.microsoft.com/en-us/power-bi/connect-data/service-datasets-understand

### Data Science
- **Data Agents**: Conversational AI over Fabric data sources
  - Docs: https://learn.microsoft.com/en-us/fabric/data-science/concept-data-agent
- **Data Agent Evaluation**: Testing and validating Data Agent accuracy
  - Docs: https://learn.microsoft.com/en-us/fabric/data-science/fabric-data-agent-sdk

## Best Practices

### Must
- Use Delta Lake format for Lakehouse tables
- Include time filters in KQL queries
- Handle credentials via environment variables or Key Vault
- Use parameterized notebooks and pipelines

### Prefer
- Medallion architecture (Bronze/Silver/Gold) for data organization
- REST APIs for programmatic management
- Incremental processing over full refreshes
- mssparkutils for Fabric-specific notebook operations

### Avoid
- Hardcoded workspace/item IDs
- SELECT * without LIMIT on large tables
- Long-running transactions in Warehouse
- Unbounded streaming queries
