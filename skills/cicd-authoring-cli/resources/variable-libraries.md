# Variable Libraries for CI/CD

This resource covers using Fabric variable libraries to manage environment-specific configuration across deployment stages. Variable libraries are the recommended approach for centralised, stage-aware configuration management.

> Ref: https://learn.microsoft.com/fabric/cicd/variable-library/variable-library-overview

## When to Use

- Items need different values per environment (dev/test/prod) — e.g., lakehouse IDs, connection strings, parameters
- Multiple items in a workspace share the same configuration values
- You want to avoid hardcoding GUIDs in notebook `%%configure` blocks or pipeline activities
- You need a Fabric-native alternative to `parameter.yml` GUID replacement
- You want configuration changes to propagate automatically to consuming items without redeployment

### Variable Libraries vs parameter.yml

| Aspect | Variable Libraries | parameter.yml (fabric-cicd) |
|---|---|---|
| **Where config lives** | Fabric workspace item (deployed alongside other items) | File in Git repo alongside item definitions |
| **When replacement happens** | Runtime — item resolves value from active value set | Deploy-time — GUIDs replaced in definitions before upload |
| **Config changes require** | Update active value set (no redeployment needed) | Re-run deployment pipeline |
| **Supported consumers** | Pipelines, Notebooks, Dataflows Gen2, Lakehouses (shortcuts), Copy Jobs, User Data Functions | Any item definition file (text-level find/replace) |
| **Variable types** | String, Integer, Number, Boolean, DateTime, Guid, Item Reference, Connection Reference | String find/replace only |
| **Best for** | Runtime configuration, item-to-item references, connection switching | Workspace/lakehouse GUID replacement in definition files |

**Recommendation**: Use variable libraries for runtime configuration (connections, item references, parameters). Use `parameter.yml` only for GUIDs that are baked into item definitions at deploy time and cannot be resolved at runtime (e.g., `%%configure` lakehouse IDs if not using variable library syntax).

## Core Concepts

### Variable Types

| Type | Category | Description | Example |
|---|---|---|---|
| String | Basic | Text values | `"prod-server.database.windows.net"` |
| Integer | Basic | Whole numbers | `30` (wait time in seconds) |
| Number | Basic | Decimal numbers | `0.95` (threshold) |
| Boolean | Basic | True/false | `true` (enable feature flag) |
| DateTime | Basic | ISO 8601 UTC format | `"2026-01-01T00:00:00.000Z"` |
| Guid | Basic | GUID identifier | `"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"` |
| Item Reference | Advanced | Pointer to a Fabric item (workspace ID + item ID) | Reference to a specific lakehouse |
| Connection Reference | Advanced | Pointer to an external data connection | Reference to a Snowflake or Azure SQL connection |

### Value Sets

Value sets provide alternative values for different deployment stages:

- **Default value set**: Always present, contains baseline values for every variable
- **Alternative value sets**: Override specific variables for each stage (e.g., `Test`, `Prod`)
- Only variables that **differ** from the default need to be specified in alternative sets
- **One value set is active** per workspace at any time
- The active value set determines which values consuming items receive at runtime
- Changing the active value set does NOT require redeployment — it takes effect immediately

```text
Variable Library: "EnvConfig"
├── Default (active in Dev workspace)
│   ├── LakehouseName = "sales-dev"
│   ├── ServerUrl = "dev-server.database.windows.net"
│   └── BatchSize = 1000
├── Test (active in Test workspace)
│   ├── LakehouseName = "sales-test"      ← overrides default
│   └── ServerUrl = "test-server.database.windows.net"  ← overrides default
│   (BatchSize uses default: 1000)
└── Prod (active in Prod workspace)
    ├── LakehouseName = "sales-prod"
    ├── ServerUrl = "prod-server.database.windows.net"
    └── BatchSize = 5000                   ← overrides default
```

### Active Value Set Behaviour in CI/CD

This is critical to understand:

- When you deploy a variable library to a new workspace, the **default** value set is activated
- You must **manually or programmatically set the active value set** in each target workspace after deployment
- The active value set selection is **not part of the item definition** — it's workspace-level state
- Deployments do NOT overwrite the active value set — it persists across deployments
- After first-time setup, the active value set stays correct even through subsequent deployments

## How Items Consume Variables

### Notebooks — via NotebookUtils

```python
# Get the full library object (dot notation access)
myvl = notebookutils.variableLibrary.getLibrary("MyVarLib")
lakehouse_name = myvl.LakehouseName
server_url = myvl.ServerUrl

# Or access a single variable by reference
lakehouse_name = notebookutils.variableLibrary.get("$(/**/MyVarLib/LakehouseName)")
```

**Best practices for notebooks:**
- Assign variable values to local variables first — avoid inline `notebookutils.variableLibrary.get()` in loops (causes throttling)
- `notebookutils.variableLibrary` only accesses libraries within the same workspace
- Cross-workspace access is NOT supported in child notebooks during reference runs
- The notebook resolves values from the **active value set** in its workspace

### Notebooks — via %%configure (Default Lakehouse)

Use variable library to dynamically set the default lakehouse without hardcoding GUIDs:

```json
%%configure
{
  "defaultLakehouse": {
    "name": {
      "variableName": "$(/**/MyVarLib/LHname)"
    },
    "id": {
      "variableName": "$(/**/MyVarLib/LHid)"
    },
    "workspaceId": {
      "variableName": "$(/**/MyVarLib/WorkspaceId)"
    }
  }
}
```

All variables for `%%configure` must be **String type** in the variable library, even for GUID values. Place `%%configure` in the first code cell of the notebook.

### Pipelines — via Library Variables

In pipeline activities, use `@pipeline().libraryVariables.<VariableName>` for dynamic content:

1. Add the variable library to the pipeline's library variable references
2. In activity settings, select **Add dynamic content**
3. Select **Library variables** and choose the variable
4. The expression `@pipeline().libraryVariables.MyVariable` is inserted

This works for connections, workspace IDs, table names, file paths, and any activity parameter.

### Lakehouse Shortcuts

Assign variable library variables to shortcut target paths, allowing the same shortcut definition to point to different data sources per environment.

## Git Integration

Variable library items are stored as folders in Git:

```text
MyVarLib.VariableLibrary/
├── .platform                    # Item metadata (type, displayName, logicalId)
├── settings.json                # Library settings
├── variables.json               # Variable names, types, and default values
└── valueSets/
    ├── Test.json                # Overrides for Test value set
    └── Prod.json                # Overrides for Prod value set
```

### variables.json structure

```json
{
  "variables": [
    {
      "name": "LakehouseName",
      "type": "String",
      "value": "sales-dev",
      "note": "Target lakehouse for data ingestion"
    },
    {
      "name": "SourceLH",
      "type": "ItemReference",
      "value": {
        "workspaceId": "aaaaaaaa-0000-1111-2222-bbbbbbbbbbbb",
        "itemId": "00aa00aa-bb11-cc22-dd33-44ee44ee44ee"
      },
      "note": "Source lakehouse reference"
    },
    {
      "name": "PrimaryDb",
      "type": "connectionReference",
      "value": {
        "connectionId": "cccccccc-0000-1111-2222-dddddddddddd"
      },
      "note": "External database connection"
    }
  ]
}
```

### Value set file (e.g., Prod.json)

Only includes variables that differ from the default:

```json
{
  "variables": [
    {
      "name": "LakehouseName",
      "value": "sales-prod"
    },
    {
      "name": "SourceLH",
      "value": {
        "workspaceId": "bbbbbbbb-0000-1111-2222-cccccccccccc",
        "itemId": "11bb11bb-cc22-dd33-ee44-55ff55ff55ff"
      }
    }
  ]
}
```

## Deploying Variable Libraries

### With fabric-cicd

`VariableLibrary` is a supported item type in `fabric-cicd`. Include it in `item_type_in_scope`:

```python
target = FabricWorkspace(
    workspace_id="<workspace-id>",
    repository_directory="./fabric_items",
    environment="prod",
    item_type_in_scope=["Notebook", "DataPipeline", "Lakehouse", "VariableLibrary"],
)
publish_all_items(target)
```

The variable library deploys alongside other items. After first deployment to a new workspace, set the active value set via API.

### With Deployment Pipelines

Variable libraries are supported in Fabric deployment pipelines. When deployed between stages:

- All value sets are deployed to the target stage
- The **active value set is NOT changed** by deployment — it persists from the previous configuration
- After first deployment, manually or programmatically set the correct active value set

### Setting Active Value Set via API

After deploying to a new workspace, activate the correct value set:

```bash
# Get the variable library ID in the target workspace
az rest --method get \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<workspaceId>/variableLibraries" \
  --query "value[?displayName=='MyVarLib'].id" -o tsv

# Update the active value set
az rest --method patch \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<workspaceId>/variableLibraries/<varLibId>" \
  --body '{
    "properties": {
      "activeValueSetName": "Prod"
    }
  }'
```

> Ref: https://learn.microsoft.com/rest/api/fabric/variablelibrary/items/update-variable-library

### REST API Reference

| Operation | Method | Endpoint |
|---|---|---|
| Create | POST | `/v1/workspaces/{wsId}/variableLibraries` |
| Get (with active value set) | GET | `/v1/workspaces/{wsId}/variableLibraries/{id}` |
| Update (set active value set) | PATCH | `/v1/workspaces/{wsId}/variableLibraries/{id}` |
| Delete | DELETE | `/v1/workspaces/{wsId}/variableLibraries/{id}` |
| List | GET | `/v1/workspaces/{wsId}/variableLibraries` |
| Get definition | POST | `/v1/workspaces/{wsId}/variableLibraries/{id}/getDefinition` |
| Update definition | POST | `/v1/workspaces/{wsId}/variableLibraries/{id}/updateDefinition` |

All variable library APIs support service principals.

> Ref: https://learn.microsoft.com/fabric/cicd/variable-library/automate-variable-library

## Integration with Each Deployment Approach

### Local Deployment (fabric-cicd)

1. Author `variables.json` and value set files locally in the item folder
2. Deploy with `publish_all_items()` — the variable library is created/updated
3. After deployment, set the active value set via REST API
4. Consuming items (notebooks, pipelines) automatically pick up the active values

### GitHub Actions / Azure DevOps

1. Variable library definition lives in Git alongside other items
2. `fabric-cicd` deploys it as part of the standard deployment
3. Add a **post-deployment step** to the workflow/pipeline that sets the active value set via REST API
4. This only needs to be done on first deployment — subsequent deployments preserve the active selection

### Deployment Pipelines

1. Variable library deploys between stages automatically
2. Active value set persists per stage — set once, preserved across deployments
3. Use deployment pipeline comparison to see which variables differ between stages

## Considerations and Limitations

- Up to **1,000 variables** and **1,000 value sets** per library (total cells < 10,000, size < 1 MB)
- Variable names must be unique within a library (case-insensitive)
- `notebookutils.variableLibrary` only works within the same workspace — no cross-workspace access
- Item reference variables are **static pointers** — they don't auto-bind when deploying to a new workspace. Use value sets to define the correct item per stage
- Connection reference variables also don't auto-bind — set the correct connection ID per stage
- Changing a variable's type resets all values across value sets (breaking change for consumers)
- Active value set selection is workspace state, not part of the definition — it's NOT stored in Git

> Ref: https://learn.microsoft.com/fabric/cicd/variable-library/variable-library-cicd
