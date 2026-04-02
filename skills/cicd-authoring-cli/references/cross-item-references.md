# Cross-Item Reference Patterns

This resource documents how Fabric items reference each other, and how those references survive deployment across environments (dev → test → prod). Understanding these patterns is essential for building reliable CI/CD.

> **Key principle**: Items often contain GUIDs that point to other items (lakehouses, connections, semantic models). These GUIDs differ per environment. The CI/CD approach you choose determines how these references are resolved.

---

## Reference Resolution Approaches

There are three ways to handle cross-item references across environments:

| Approach | When Resolution Happens | How It Works | Best For |
|---|---|---|---|
| **`parameter.yml`** | Deploy-time | `fabric-cicd` finds GUIDs in item definitions and replaces them with target environment values | GUIDs baked into item definitions (e.g., notebook metadata, pipeline activity config) |
| **Variable libraries** | Runtime | Items resolve references from the active value set in their workspace at execution time | Runtime configuration (connections, server URLs, lakehouse names) |
| **Deployment pipeline autobinding** | Promotion-time | Fabric automatically rebinds paired items when deploying between stages | Reports → semantic models, and other Fabric-managed bindings |

### When to use which

| Scenario | Recommended Approach |
|---|---|
| Notebook `default_lakehouse` GUID in metadata | `parameter.yml` (Approach A) or variable library `%%configure` (Approach B — recommended) |
| Notebook referencing a lakehouse by name at runtime | Variable library via `notebookutils.variableLibrary` |
| Pipeline activity referencing a notebook by ID | `parameter.yml` — replace the notebook ID per environment |
| Pipeline activity reading config values | Variable library via `@pipeline().libraryVariables` |
| Report referencing a semantic model | Autobinding (deployment pipelines) or `parameter.yml` (`fabric-cicd`) |
| Copy job source/destination connections | Variable library with connection reference variables |
| Dataflow Gen2 data source connections | Variable library with connection reference variables |

---

## Pattern 1: Notebook → Lakehouse

This is the **most common** cross-item reference and the source of the most CI/CD issues.

### The Problem

Notebooks that use `spark.read.table()` or `saveAsTable()` need a default lakehouse. The notebook metadata contains three GUIDs that differ per environment:

```text
default_lakehouse: <lakehouse-item-guid>
default_lakehouse_name: MyLakehouse
default_lakehouse_workspace_id: <workspace-guid>
```

### Solution A — `parameter.yml` (deploy-time replacement)

Hardcode the **dev** environment GUIDs in the notebook metadata. Add find/replace rules in `parameter.yml`:

```yaml
find_replace:
  # Dev workspace GUID → target workspace
  - find_value: "dev-workspace-guid"
    replace_value:
      test: "$workspace.$id"
      prod: "$workspace.$id"

  # Dev lakehouse GUID → target lakehouse
  - find_value: "dev-lakehouse-guid"
    replace_value:
      test: "$items.Lakehouse.MyLakehouse.$id"
      prod: "$items.Lakehouse.MyLakehouse.$id"
```

`fabric-cicd` replaces these GUIDs in the notebook definition before uploading to the target workspace.

**Pros**: Simple, well-understood, works with any notebook format.
**Cons**: Requires maintaining `parameter.yml`; notebook definitions differ per environment after deployment.

### Solution B — Variable library `%%configure` (runtime resolution, recommended)

Instead of hardcoding GUIDs, use `%%configure` in the first notebook cell to resolve the lakehouse from a variable library:

```json
%%configure
{
  "defaultLakehouse": {
    "name": { "variableName": "$(/**/MyVarLib/LHname)" },
    "id": { "variableName": "$(/**/MyVarLib/LHid)" },
    "workspaceId": { "variableName": "$(/**/MyVarLib/WorkspaceId)" }
  }
}
```

The variable library `MyVarLib` has value sets for each environment with the correct GUIDs. The same notebook definition deploys to every workspace unchanged.

**Pros**: No `parameter.yml` needed for lakehouse GUIDs; one notebook definition works everywhere; config changes don't require redeployment.
**Cons**: Requires variable library setup; all `%%configure` variables must be **String type** (even for GUIDs); variable library must be deployed first.

### Solution C — Runtime lookup via `notebookutils`

For dynamic references that aren't the default lakehouse:

```python
import notebookutils

vl = notebookutils.variableLibrary.getLibrary("MyVarLib")
lakehouse_name = vl.LakehouseName
server_url = vl.ServerUrl
```

**Best for**: Reading configuration values at runtime (server URLs, feature flags, batch sizes). Not suitable for `default_lakehouse` binding.

---

## Pattern 2: DataPipeline → Notebook

Pipelines that invoke notebooks contain the notebook's item ID in the activity configuration. This ID differs per environment.

### Solution: `parameter.yml`

```yaml
find_replace:
  - find_value: "dev-notebook-item-guid"
    replace_value:
      test: "$items.Notebook.MyNotebook.$id"
      prod: "$items.Notebook.MyNotebook.$id"
```

### Solution: Variable library

In pipeline activities, use dynamic content with library variables:

```text
@pipeline().libraryVariables.NotebookId
```

This resolves the notebook ID from the variable library's active value set at runtime.

---

## Pattern 3: DataPipeline → Lakehouse/Warehouse

Pipelines that read from or write to lakehouses/warehouses contain item IDs in activity configurations.

### Solution: Variable library (recommended)

Define item reference variables or GUID string variables in the variable library:

```text
@pipeline().libraryVariables.TargetLakehouseId
@pipeline().libraryVariables.TargetWarehouseId
```

### Solution: `parameter.yml`

```yaml
find_replace:
  - find_value: "dev-lakehouse-guid-in-pipeline"
    replace_value:
      test: "$items.Lakehouse.MyLakehouse.$id"
      prod: "$items.Lakehouse.MyLakehouse.$id"
```

---

## Pattern 4: Report → SemanticModel

Reports reference their data source semantic model. This reference must point to the correct model per environment.

### With Deployment Pipelines: Autobinding (automatic)

When using Fabric deployment pipelines, paired reports and semantic models are automatically rebound. If `MyReport` is paired with `MyModel` in dev, deploying to test automatically binds the test copy of `MyReport` to the test copy of `MyModel`. No configuration needed.

### With `fabric-cicd`: `parameter.yml`

Reports in PBIR format contain a `byConnection` reference with a dataset ID. Replace it per environment:

```yaml
find_replace:
  - find_value: "dev-semantic-model-guid"
    replace_value:
      test: "$items.SemanticModel.MyModel.$id"
      prod: "$items.SemanticModel.MyModel.$id"
```

> `fabric-cicd` handles dependency ordering — semantic models deploy before reports automatically.

---

## Pattern 5: CopyJob → Connections

Copy jobs contain source and destination connection references that differ per environment (e.g., dev SQL server vs prod SQL server).

### Solution: Variable library with connection reference variables

Define connection reference variables in the variable library with different connection IDs per value set. The copy job resolves the correct connection at runtime.

### Solution: `parameter.yml`

Replace the connection GUID in the copy job definition:

```yaml
find_replace:
  - find_value: "dev-connection-guid"
    replace_value:
      test: "test-connection-guid"
      prod: "prod-connection-guid"
```

> **Note**: Connection reference variables store a Fabric **connection ID** (a GUID), not the actual connection credentials. The credentials live in the Fabric connection object itself.

---

## Pattern 6: Variable Library → All Consumers

Variable libraries are consumed by multiple item types. Deploy them early in the deployment order, and set the active value set after deployment.

### Consumer Reference Patterns

| Consumer | How It References Variables | Example |
|---|---|---|
| **Notebook** (runtime) | `notebookutils.variableLibrary.getLibrary("VarLib")` | `vl.ServerUrl` |
| **Notebook** (default lakehouse) | `%%configure` with `variableName` syntax | See Pattern 1, Solution B |
| **DataPipeline** | `@pipeline().libraryVariables.<VarName>` | Dynamic content in activity settings |
| **Dataflow Gen2** | Variable reference in dataflow parameters | Bind to variable library variables in UI |
| **Lakehouse** (shortcuts) | Shortcut target path from variable | Environment-specific shortcut destinations |
| **Copy Job** | Connection reference variables | Source/destination connection per environment |

### Deployment Order for Variable Libraries

1. Deploy the variable library item (include `"VariableLibrary"` in `item_type_in_scope`)
2. Set the active value set via API: `PATCH /v1/workspaces/{id}/variableLibraries/{varLibId}` with `{"properties": {"activeValueSetName": "<env>"}}`
3. Deploy consuming items (notebooks, pipelines, etc.)
4. Consuming items automatically pick up the correct values from the active value set

> **Important**: Step 2 only needs to happen on the **first deployment** to a workspace. The active value set persists across subsequent deployments.

---

## Decision Tree: How to Handle Cross-Item References

```text
Does the item definition contain a GUID from another item?
├── YES → Is the GUID in notebook default_lakehouse metadata?
│   ├── YES → Use variable library %%configure (recommended) or parameter.yml
│   └── NO → Use parameter.yml with $items.<Type>.<Name>.$id tokens
└── NO → Does the item need environment-specific config at runtime?
    ├── YES → Is it a connection/data source?
    │   ├── YES → Use variable library with connection reference variables
    │   └── NO → Use variable library with String/Guid variables
    └── NO → No cross-item reference handling needed
```

---

## Common Pitfalls

| Pitfall | What Happens | Fix |
|---|---|---|
| Missing `default_lakehouse_workspace_id` | Notebook deploys but fails at runtime | Always include all three lakehouse fields in metadata |
| Variable library deployed but wrong value set active | Items use dev config in prod | Set active value set via API after first deployment |
| `parameter.yml` `environment` doesn't match value set key | GUIDs not replaced — items contain dev GUIDs | Ensure `FabricWorkspace(environment=...)` matches a key in `replace_value` |
| Item reference variable points to non-existent item | Deploy fails with `ReferencedEntityAccessDenied` | Ensure SPN has read access to all referenced items |
| Mixing `parameter.yml` and variable libraries for the same GUID | Confusing behavior — double replacement possible | Choose one approach per reference and be consistent |
